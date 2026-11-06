#!/usr/bin/env python3
"""P.A.P.E. receipts: the engine behind the I.N-D.O.C.-T.R.I.N. 8-P.I.E.C.E. Mac app.

Receipt scans, phone photos or PDFs -> text (Tesseract, on this computer) -> store, date, time, line items,
subtax, tax, total, payment -> a receipt folder with custody files + receipts.csv / items.csv ledgers.
Ported from the M.A.R.K. Receipt Processor heuristics. Standard library only; calls tesseract/pdftotext/pdftoppm/sips.
Nothing is uploaded. The optional "check with a local model" step talks only to Ollama on this computer.

  python3 pape_receipt.py check
  python3 pape_receipt.py read FILE [FILE ...] [--model gemma4:12b]
  python3 pape_receipt.py scan [--model ...]          # ScanSnap feeder, one receipt per page (front side)
  python3 pape_receipt.py inbox [--model ...]         # read everything dropped in <out>/inbox, then move it to inbox/done
  python3 pape_receipt.py ledger [--limit 50]
  python3 pape_receipt.py dedupe                      # mark rescans of the same receipt (store+date+time+total+trans #)
  python3 pape_receipt.py recon                       # run queued store look-ups (store's own website only)
  python3 pape_receipt.py stores                      # the store catalog (also <out>/stores.csv)
  python3 pape_receipt.py report                      # month x category / store / card totals -> <out>/reports/*.csv

Output: JSON on stdout. Files: ${PAPE_RECEIPTS:-~/pape_scans/receipts}.
Layout: each scan also gets rows.csv (every text line with its x, y, width, height and confidence, 0-1 of the page),
a document type guess (receipt, form, table, letter, document) and a field map (where store, date, items, total and
payment sit). Each store's map is averaged into templates/<store>.json and used to find a missing total next time.
Best OCR: RapidOCR (PP-OCR on ONNX) + OpenCV from the P.A.P.E. venv, trying upright, upside down and mirrored
(receipts fed wrong side up are read through the paper). Fallback: Tesseract.
Load rule: one job at a time (lock file), background priority, a timeout on every OCR call.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import math
import statistics
from datetime import date, datetime
from pathlib import Path

VERSION = "0.2.0"
OUT = Path(os.environ.get("PAPE_RECEIPTS", Path.home() / "pape_scans" / "receipts")).expanduser()
OCR_TIMEOUT = int(os.environ.get("PAPE_OCR_TIMEOUT", "120"))
IMAGES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff", ".bmp", ".gif"}
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "/usr/bin:/bin")

# Store name patterns: (text to look for, name to show, category). The public engine ships with none; each owner adds
# their own stores in <out>/local_rules.json (kept private, next to the ledger). New stores are also learned as templates.
STORES = []
CARE_WORDS = ("vitamin", "supplement", "medicine", "bandage", "gauze", "incontinence", "brief", "glove", "wipes",
              "nutrition shake", "pharmacy", "rx ", "thermometer", "pill", "lotion", "chux", "underpad")
NOT_ITEMS = ("subtotal", "sub total", "sub tetal", "sub totai", "tetal", "total", "tax", "change", "cash", "visa", "mastercard", "master card", "amex",
             "discover", "debit", "credit", "ebt", "snap", "balance", "tend", "amount", "approv", "auth", "card #",
             "acct", "account", "you saved", "savings", "points", "reward", "items sold", "item count", "tip",
             "ref #", "trans", "invoice", "usd", "qty", "amount", "store #", "receipt", "thank", "survey", "aid:", "tvr", "entry method")
PRICE_END = re.compile(r"(-?)\$?\s?(\d{1,5}[.,]\d{2})\s*(-)?\s*(?:[A-Z]{1,2}|\*|[A-Z]\s?[A-Z])?\s*$")
MONEY = re.compile(r"-?\$?\s?(\d{1,6}[.,]\d{2})")


_LOCAL = {}


def local_rules():
    """The owner's private rules (<out>/local_rules.json): their stores and extra item words. Never shipped."""
    if "v" not in _LOCAL:
        try:
            _LOCAL["v"] = json.loads((OUT / "local_rules.json").read_text())
        except (OSError, ValueError):
            _LOCAL["v"] = {}
    return _LOCAL["v"]


def known_stores():
    return [tuple(x) for x in local_rules().get("stores", []) if len(x) == 3] + STORES


def care_words():
    return CARE_WORDS + tuple(w.lower() for w in local_rules().get("words", {}).get("care & medical", []))


# ---------- load guard ----------
def background():
    try:
        os.nice(15)
    except OSError:
        pass


def run(cmd, timeout=OCR_TIMEOUT):
    pre = ["taskpolicy", "-b"] if shutil.which("taskpolicy") else []
    p = subprocess.run(pre + cmd, capture_output=True, text=True, timeout=timeout)
    return p.stdout


class Lock:
    def __enter__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.f = open(OUT / ".lock", "w")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            emit({"ok": False, "error": "Another receipt job is running. Wait for it to finish."})
            sys.exit(3)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def emit(obj):
    print(json.dumps(obj, indent=1, default=str))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ---------- OCR ----------
_RAPID = None


def rapid():
    """RapidOCR + OpenCV if this Python has them (the P.A.P.E. venv does). None = use Tesseract."""
    global _RAPID
    if _RAPID is None:
        try:
            import logging
            import cv2  # noqa: F401
            from rapidocr import RapidOCR
            logging.disable(logging.INFO)
            threads = int(os.environ.get("PAPE_THREADS", "4"))  # keep the Mac usable while it reads
            try:
                _RAPID = RapidOCR(params={"Global.use_cls": False,
                                          "EngineConfig.onnxruntime.intra_op_num_threads": threads,
                                          "EngineConfig.onnxruntime.inter_op_num_threads": 1})
            except Exception:
                _RAPID = RapidOCR()
        except Exception:
            _RAPID = False
    return _RAPID or None


def clean_image(path: Path, tmp: Path):
    import cv2
    import numpy as np
    src = path
    if path.suffix.lower() in (".heic", ".heif", ".webp", ".gif"):
        src = tmp / (path.stem + ".png")
        run(["sips", "-s", "format", "png", str(path), "--out", str(src)], timeout=60)
    img = cv2.imread(str(src), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("could not open the picture")
    h, w = img.shape
    if max(h, w) > 3600:
        f = 3600 / max(h, w)
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    # flatten the background (crumples, shadows, gray paper), then stretch the faint thermal print
    bg = cv2.medianBlur(cv2.dilate(img, np.ones((7, 7), np.uint8)), 31)
    return cv2.normalize(255 - cv2.absdiff(img, bg), None, 0, 255, cv2.NORM_MINMAX)


def read_rapid(img):
    """Try upright first; only try the other ways when the read is weak. Returns (rows, way, image)."""
    import cv2
    eng = rapid()
    ways = [("upright", lambda i: i), ("upside down", lambda i: cv2.rotate(i, cv2.ROTATE_180)),
            ("mirrored (read through the back)", lambda i: cv2.flip(i, 1)),
            ("mirrored, upside down (read through the back)", lambda i: cv2.flip(i, 0))]
    if img.shape[1] > img.shape[0] * 1.3:  # wide picture: maybe a phone photo taken sideways
        ways += [("turned left", lambda i: cv2.rotate(i, cv2.ROTATE_90_CLOCKWISE)),
                 ("turned right", lambda i: cv2.rotate(i, cv2.ROTATE_90_COUNTERCLOCKWISE))]
    best = None
    for name, fn in ways:
        im = fn(img)
        r = eng(im, use_cls=False) if _accepts_cls(eng) else eng(im)
        txts = list(r.txts or [])
        score = sum(r.scores) if txts else 0.0
        if not best or score > best[0]:
            best = (score, name, r, im)
        mean = score / len(txts) if txts else 0
        if name == "upright" and mean >= 0.9 and len(txts) >= 8:
            break
    score, name, r, im = best
    return boxes_to_rows(r, im.shape[1], im.shape[0]), name, im


def _accepts_cls(eng):
    try:
        import inspect
        return "use_cls" in inspect.signature(eng.__call__).parameters
    except (TypeError, ValueError):
        return False


def boxes_to_rows(r, W, H):
    """Put text boxes back into printed lines: correct the tilt, group by height, sort left to right."""
    if not r.txts:
        return []
    boxes = []
    slopes = []
    for b, t, sc in zip(r.boxes, r.txts, r.scores):
        xs, ys = [float(p[0]) for p in b], [float(p[1]) for p in b]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        dx, dy = float(b[1][0] - b[0][0]), float(b[1][1] - b[0][1])
        if dx > 3 * (y1 - y0):
            slopes.append(dy / dx)
        boxes.append({"t": t, "s": float(sc), "x0": x0, "x1": x1, "y0": y0, "y1": y1, "xc": (x0 + x1) / 2,
                      "yc": (y0 + y1) / 2, "h": y1 - y0})
    slope = statistics.median(slopes) if slopes else 0.0
    for b in boxes:
        b["yk"] = b["yc"] - slope * b["xc"]
    mh = statistics.median(b["h"] for b in boxes) or 10
    boxes.sort(key=lambda b: b["yk"])
    rows = []
    for b in boxes:
        # join the closest recent line that is level with it and has nothing in the same left-right space
        best = None
        for row in rows[-3:]:
            d = abs(b["yk"] - statistics.mean(c["yk"] for c in row))
            overlap = any(min(b["x1"], c["x1"]) - max(b["x0"], c["x0"]) > 0.3 * min(b["x1"] - b["x0"], c["x1"] - c["x0"])
                          for c in row)
            if d < 0.6 * mh and not overlap and (best is None or d < best[0]):
                best = (d, row)
        if best:
            best[1].append(b)
        else:
            rows.append([b])
    rows.sort(key=lambda row: statistics.mean(c["yk"] for c in row))
    rows = pair_amounts(rows, mh)
    out = []
    for row in rows:
        row.sort(key=lambda b: b["x0"])
        text = row[0]["t"]
        for a, b in zip(row, row[1:]):
            text += ("    " if b["x0"] - a["x1"] > mh else " ") + b["t"]
        x0, x1 = min(b["x0"] for b in row), max(b["x1"] for b in row)
        y0, y1 = min(b["y0"] for b in row), max(b["y1"] for b in row)
        out.append({"text": text.strip(), "x": round(x0 / W, 4), "y": round(y0 / H, 4), "w": round((x1 - x0) / W, 4),
                    "h": round((y1 - y0) / H, 4), "conf": round(min(b["s"] for b in row), 3), "boxes": len(row),
                    "cols": [round(b["x0"] / W, 3) for b in row]})
    return out


def pair_amounts(rows, mh):
    """A right-hand amount printed half a line off its label (tilted or crumpled paper) joins the label's line."""
    is_amt = lambda row: all(MONEY.fullmatch(b["t"].strip().replace(" ", "")) for b in row)
    has_amt = lambda row: any(MONEY.search(b["t"]) for b in row)
    yk = lambda row: statistics.mean(b["yk"] for b in row)
    used, merged = set(), {}
    labels = [i for i, r in enumerate(rows) if not has_amt(r)]
    amts = [i for i, r in enumerate(rows) if is_amt(r)]
    pairs = sorted((abs(yk(rows[l]) - yk(rows[a])), l, a) for l in labels for a in amts
                   if abs(yk(rows[l]) - yk(rows[a])) < 1.1 * mh
                   and min(b["x0"] for b in rows[a]) > max(b["x1"] for b in rows[l]))
    for d, l, a in pairs:
        if l in used or a in used:
            continue
        used |= {l, a}
        merged[l] = rows[l] + rows[a]
    return [merged.get(i, r) for i, r in enumerate(rows) if i not in used or i in merged]


def ocr_image(path: Path, tmp: Path, folder: Path | None = None):
    """-> (text, engine, rows, way, aspect)"""
    if rapid():
        img = clean_image(path, tmp)
        rows, way, im = read_rapid(img)
        if folder is not None:
            import cv2
            cv2.imwrite(str(folder / "clean.png"), im)
            f = 520 / im.shape[1]
            cv2.imwrite(str(folder / "preview.jpg"), cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 70])
        return "\n".join(r["text"] for r in rows), "RapidOCR", rows, way, round(im.shape[0] / im.shape[1], 2)
    src = path
    if path.suffix.lower() in (".heic", ".heif", ".webp", ".gif"):
        src = tmp / (path.stem + ".png")
        run(["sips", "-s", "format", "png", str(path), "--out", str(src)], timeout=60)
    # psm 4 = one column of text of varying sizes: how receipts are laid out
    return run(["tesseract", str(src), "stdout", "-l", "eng", "--psm", "4"]), "tesseract", [], "upright", None


def ocr_file(path: Path, folder: Path | None = None):
    """-> (text, engine, rows, way, aspect)"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if path.suffix.lower() == ".pdf":
            text = run(["pdftotext", "-layout", str(path), "-"], timeout=60)
            if len(text.split()) >= 15:
                return text, "pdf text layer", [], "upright", None
            run(["pdftoppm", "-r", "300", "-gray", "-png", "-l", "4", str(path), str(tmp / "pg")], timeout=OCR_TIMEOUT)
            pages = sorted(tmp.glob("pg*.png"))
            texts, rows, way, aspect, eng = [], [], "upright", None, "tesseract"
            for n, pg in enumerate(pages):
                t, eng, r, w, a = ocr_image(pg, tmp, folder if n == 0 else None)
                texts.append(t)
                rows += [dict(x, page=n + 1) for x in r]
                if n == 0:
                    way, aspect = w, a
            return "\n".join(texts), f"{eng} ({len(pages)} page{'s' * (len(pages) != 1)})", rows, way, aspect
        if path.suffix.lower() in (".txt", ".md"):
            return path.read_text(errors="replace"), "text file", [], "upright", None
        return ocr_image(path, tmp, folder)


# ---------- parse ----------
def money(s: str) -> float:
    return float(s.replace(",", "."))


def find_store(lines):
    blob = " ".join(lines[:15]).lower() + " " + " ".join(lines).lower()
    for needle, name, cat in known_stores():
        if needle in blob:
            return name, cat
    for ln in lines[:6]:
        if len(ln) > 3 and re.search(r"[A-Za-z]{3}", ln) and not re.match(r"^[\d#*]", ln):
            return ln.strip(" *-=").title()[:60], "other"
    return "Unknown", "other"


MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()


def find_date(text):
    today = date.today()
    cands = []
    for m in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text):
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y += 2000 if y < 100 else 0
        cands.append((y, mo, d))
    for m in re.finditer(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text):
        cands.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"\b(" + "|".join(MONTHS) + r")[a-z]*\.?\s+(\d{1,2}),?\s+(20\d{2})", text, re.I):
        cands.append((int(m.group(3)), MONTHS.index(m.group(1)[:3].lower()) + 1, int(m.group(2))))
    for y, mo, d in cands:
        try:
            dt = date(y, mo, d)
        except ValueError:
            continue
        if date(2000, 1, 1) <= dt <= today:
            return dt.isoformat()
    return None


def find_time(text):
    m = re.search(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)?", text)
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return None
    h, mi, ap = int(m.group(1)), m.group(2), (m.group(4) or "").replace(".", "").upper()
    if ap == "PM" and h < 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    return f"{h:02d}:{mi}"


def last_money(line):
    ms = MONEY.findall(line)
    return money(ms[-1]) if ms else None


def find_totals(lines):
    total = subtotal = tax = None
    totals = []
    for i, ln in enumerate(lines):
        u = ln.upper().replace(" ", "")
        v = last_money(ln)
        if v is None and i + 1 < len(lines) and re.fullmatch(r"[\s$\d.,-]+", lines[i + 1]):
            v = last_money(lines[i + 1])  # amount on the next line
        if v is None:
            continue
        if re.search(r"SUB-?T\w?TAL", u):
            subtotal = v
        elif re.search(r"TAX", u) and not re.search(r"TAXABLE|NONTAX|TAXEXEMPT", u):
            tax = v if tax is None else tax
        elif re.search(r"(GRAND)?T[O0E]T[AE]L|BALANCEDUE|AMOUNTDUE|TOTALDUE", u) and not re.search(
                r"SAVING|SAVED|ITEMS|DISCOUNT|POINTS|TAX", u):
            totals.append(v)
    if totals:
        total = max(totals)
    if total is None and subtotal is not None:
        total = round(subtotal + (tax or 0), 2)
    return total, subtotal, tax


def join_price_lines(lines):
    """'HF JR CHICKEN SANDWICH' + 'T    $2.99' (price slipped to its own line) -> one item line."""
    out = []
    for ln in lines:
        if (out and re.fullmatch(r"[A-Z*]{0,2}\s*-?\$?\s?\d{1,5}[.,]\d{2}\s*-?\s*[A-Z]?", ln.strip())
                and not MONEY.search(out[-1]) and re.search(r"[A-Za-z]{3}", out[-1])
                and not any(k in out[-1].lower() for k in NOT_ITEMS)):
            flag = re.match(r"([A-Z*]{1,2})\s", ln.strip())
            out[-1] = (flag.group(1) + " " if flag else "") + out[-1] + "    " + MONEY.search(ln).group(0)
        else:
            out.append(ln)
    return out


def find_items(lines):
    items = []
    lines = join_price_lines(lines)
    stop = next((i for i, ln in enumerate(lines) if re.search(r"SUB\s*-?\s*T\w?TAL|\bT[O0E]T[AE]L\b|\bTAX\b", ln.upper()) and MONEY.search(ln)), None)
    if stop:
        lines = lines[:stop]
    for ln in lines:
        low = ln.lower()
        if any(k in low for k in NOT_ITEMS):
            continue
        m = PRICE_END.search(ln)
        if not m:
            continue
        name = ln[: m.start()].strip(" .:$*-\t")
        if len(re.sub(r"[^A-Za-z]", "", name)) < 2:
            continue
        price = money(m.group(2))
        if m.group(1) or m.group(3):
            price = -price  # coupon or discount line
        qty = 1.0
        q = re.search(r"(\d+(?:\.\d+)?)\s*(?:@|x|X)\s*\$?\d", name)
        if q:
            qty = float(q.group(1))
            name = name[: q.start()].strip() or name
        if qty == 1.0:
            q2 = re.search(r"[A-Za-z].*?\s+(\d{1,2})$", name)   # a Qty column printed just before the amount
            if q2 and int(q2.group(1)) > 0 and not re.search(r"(PUMP|REG|REGISTER|AISLE|LANE|#)\s*$", name[: q2.start(1)].upper()):
                qty = float(q2.group(1))
                name = name[: q2.start(1)].strip()
        name = re.sub(r"^\d{4,}\s+", "", name)          # leading item/UPC numbers
        name = re.sub(r"^[A-Z]\.?\s+(?=[A-Z]{2})", "", name)  # leading tax-code letter ("T", "T.")
        name = re.sub(r"\s{2,}", " ", name)
        items.append({"name": name[:80], "quantity": qty, "price": price})
    return items[:80]


def find_payment(text):
    u = text.upper()
    if re.search(r"\bEBT\b|\bSNAP\b|FOOD ?STAMP|\bQUEST\b", u):
        m = re.search(r"(?:EBT|SNAP|FOOD ?STAMP)[^\n]*?(\d+[.,]\d{2})", u)
        return "EBT / SNAP", money(m.group(1)) if m else None
    for k, v in (("VISA", "card (Visa)"), ("MASTERCARD", "card (Mastercard)"), ("MASTER CARD", "card (Mastercard)"),
                 ("AMEX", "card (Amex)"), ("DISCOVER", "card (Discover)"), ("DEBIT", "debit card"),
                 ("CREDIT", "credit card"), ("CASH", "cash"), ("GIFT CARD", "gift card")):
        if k in u:
            return v, None
    return None, None


# ---------- location, card, categories ----------
CATEGORY_RULES = [  # (words in the item name, category). First match wins. Edit <out>/categories.json to add your own.
    (("cbd", "cbg", "cbn", "thc", "delta 8", "delta-8", "delta 9", "delta-9", "d8 ", "d9 ", "thca", "hemp", "kratom",
      "gummies", "gummy", "tincture", "pre-roll", "preroll", "pre roll", "flower", "cart ", "cartridge", "disposable",
      "topical", "salve", "edible"), "cbd & hemp"),
    (("prepay fuel", "unleaded", "diesel", "gasoline", "fuel pump", "premium fuel", "e85", "pump #"), "fuel"),
    (("beer", "lager", "ipa", "wine", "vodka", "whiskey", "rum ", "hard seltzer", "malt"), "alcohol"),
    (("menthol", "cigar", "cigarette", "vape", "pod ", "tobacco", "snus", "nicotine", "lighter"), "tobacco & vape"),
    (CARE_WORDS, "care & medical"),
    (("ftn", "fountain", "refill", "cola", "soda", "pop ", "tea", "coffee", "cappuccino",
      "water", "juice", "sparkling", "energy", "sports drink", "milk", "drink"), "drinks"),
    (("bread", "donut", "bun", "sandwich", "chicken", "pizza", "burger", "hot dog", "taco", "burrito",
      "banana", "apple", "egg", "cheese", "chips", "candy", "cookie", "snack", "meal", "salad", "fruit", "soup",
      "cereal", "jerky", "nuts"), "food"),
    (("paper towel", "toilet", "tissue", "detergent", "soap", "bleach", "trash bag", "foil", "battery", "bulb",
      "cleaner", "sponge", "dish"), "household"),
    (("stamp", "postage", "shipping"), "postage"),
]


def category_rules():
    extra = OUT / "categories.json"
    rules = []
    if extra.exists():
        try:
            rules = [(tuple(w.lower() for w in v), k) for k, v in json.loads(extra.read_text()).items()]
        except (ValueError, AttributeError):
            pass
    mine = [(tuple(w.lower() for w in v), k) for k, v in local_rules().get("words", {}).items()]
    return rules + mine + CATEGORY_RULES


def categorize(item, store_category):
    if item["price"] < 0:
        return "discount"
    n = " " + item["name"].lower() + " "
    for words, cat in category_rules():
        if any(w in n for w in words):
            # at a specialty shop (CBD, pharmacy, hardware...), a loose food/drink word is usually a product name
            # ("Cotton Candy" strain): the shop's own category wins
            if cat in ("food", "drinks") and store_category in ("cbd & hemp", "pharmacy", "hardware", "thrift",
                                                               "electronics", "clothing"):
                return store_category
            return cat
    return store_category or "other"


STATES = {"alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
          "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
          "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
          "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
          "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
          "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
          "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
          "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
          "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
          "wisconsin": "WI", "wyoming": "WY"}


def find_location(lines):
    head = lines[:10]
    loc = {"address": None, "city": None, "state": None, "zip": None, "phone": None, "store_number": None,
           "email": None}
    # city / state / zip printed on separate lines: "Anytown" / "Ohio" / "12345"
    for i, ln in enumerate(head):
        st = STATES.get(ln.strip().lower().rstrip(","))
        if st and not loc["state"]:
            loc["state"] = st
            if i > 0 and re.fullmatch(r"[A-Za-z .'-]{3,30}", head[i - 1].strip()):
                loc["city"] = head[i - 1].strip().title()
            if i + 1 < len(head) and re.fullmatch(r"\d{5}(-\d{4})?", head[i + 1].strip()):
                loc["zip"] = head[i + 1].strip()[:5]
    for ln in lines[:14]:
        m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", ln)
        if m and not loc["email"]:
            loc["email"] = m.group(0).lower()
    for ln in head:
        m = re.search(r"([A-Za-z .'-]+),?\s+([A-Z]{2})\s+(\d{5})(?:-\d{4})?", ln)
        if m and not loc["zip"]:
            loc.update(city=m.group(1).strip().title(), state=m.group(2), zip=m.group(3))
        m = re.search(r"\b(\d{2,6}[- ][\w .'-]*?\b(st|street|ave|avenue|rd|road|dr|drive|blvd|hwy|highway|ln|lane|way|pkwy|ct|pl)\b\.?)",
                      ln, re.I)
        if m and not loc["address"]:
            loc["address"] = re.sub(r"(\d+)-(\d+\w*)", r"\1 \2", m.group(1)).strip()
        m = re.search(r"\(?\b(\d{3})\)?[-. ](\d{3})[-. ](\d{4})\b", ln)
        if m and not loc["phone"]:
            loc["phone"] = "-".join(m.groups())
    for ln in lines[:14]:
        m = re.search(r"\bST[O0E]R[E]?\s*#?\s*:?\s*(\d{1,6})", ln.upper())
        if m:
            loc["store_number"] = m.group(1)
            break
    return loc


def find_card(lines, pay):
    """Last 4 of the card used to pay, never the loyalty/rewards card. Cash -> 'cash'."""
    for i, ln in enumerate(lines):
        m = re.search(r"(?:[X*#•]{4,}[\s-]*|ENDING\s+(?:IN\s+)?|ACCT\s*#?\s*:?\s*[X*]*)(\d{4})\b", ln.upper())
        if not m:
            continue
        near = " ".join(lines[max(0, i - 2): i + 1]).lower()
        if any(w in near for w in ("reward", "loyalty", "member", "points", "perks", "club card")):
            continue
        return m.group(1)
    return "cash" if pay == "cash" else None


def parse(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    store, category = find_store(lines)
    total, subtotal, tax = find_totals(lines)
    items = find_items(lines)
    pay, ebt = find_payment(text)
    words = len(text.split())
    flags = []
    if words < 15:
        flags.append("little text read: rescan flatter or brighter")
    if total is None:
        flags.append("no total found")
    when = find_date(text)
    if not when:
        flags.append("no date found")
    item_sum = round(sum(i["price"] for i in items), 2)  # printed amounts are line totals
    for i in items:
        if i["quantity"] > 1:
            i["each"] = round(i["price"] / i["quantity"], 2)
    check = subtotal if subtotal is not None else (round(total - (tax or 0), 2) if total is not None else None)
    if check is not None and items and abs(item_sum - check) > 0.05:
        flags.append(f"items add up to {item_sum:.2f}, receipt says {check:.2f}: check the lines")
    care = [i["name"] for i in items if any(w in i["name"].lower() for w in care_words())]
    loc = find_location(lines)
    card = find_card(lines, pay)
    site = None
    for m in re.finditer(r"\b((?:https?://)?(?:www\.)?[a-z0-9][a-z0-9-]{1,62}\.(?:com|net|org|shop|store|co|us|biz|info)(?:/[\w/-]*)?)\b",
                         text, re.I):
        cand = m.group(1).lower()
        if "@" not in text[max(0, m.start() - 1):m.start()] and not re.match(r"^\d", cand):
            site = re.sub(r"^https?://", "", cand).rstrip("/")
            break
    trans = re.search(r"TRANS(?:ACTION)?\.?\s*-?\s*(?:#|NO\.?|NUM(?:BER)?)?\s*:?\s*(\d{3,})", text.upper())
    reg = re.search(r"REG(?:ISTER)?\.?\s*#?\s*:?\s*(\d{1,3})\b", text.upper())
    for it in items:
        it["category"] = categorize(it, category)
    by_cat = {}
    for it in items:
        by_cat[it["category"]] = round(by_cat.get(it["category"], 0) + it["price"], 2)
    return {
        "store": store, "category": category, **loc, "card_last4": card, "spend_by_category": by_cat,
        "header": " | ".join(lines[:4])[:200],
        "website": site, "trans_number": trans.group(1) if trans else None, "register": reg.group(1) if reg else None,
        "date": when, "time": find_time(text),
        "subtotal": subtotal, "tax": tax, "total": total, "items": items, "item_sum": item_sum,
        "payment": pay, "ebt_amount": ebt, "care_items": care, "flags": flags, "words": words,
    }


# ---------- layout, document type, store templates ----------
FIELD_TESTS = {
    "date": lambda t: bool(re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b20\d{2}-\d{1,2}-\d{1,2}\b", t)),
    "time": lambda t: bool(re.search(r"\b\d{1,2}:\d{2}", t)),
    "subtotal": lambda t: bool(re.search(r"SUB\s*-?\s*TOTAL", t.upper())),
    "tax": lambda t: bool(re.search(r"\bTAX\b", t.upper())) and "TAXABLE" not in t.upper(),
    "total": lambda t: bool(re.search(r"(?<!SUB )(?<!SUB)\bTOTAL\b|BALANCE DUE|AMOUNT DUE", t.upper()))
                       and not re.search(r"SUB|SAVING|ITEMS|VISITS|TAX", t.upper()),
    "payment": lambda t: bool(re.search(r"VISA|MASTERCARD|DEBIT|CREDIT|\bCASH\b|\bEBT\b|AMEX|DISCOVER", t.upper())),
}


def layout_of(rows, rec, aspect):
    """Where things are (0 = top/left, 1 = bottom/right) and what kind of paper this is."""
    if not rows:
        return {"doc_type": guess_type_text(rec), "fields": {}, "aspect": aspect}
    fields = {}
    store = (rec.get("store") or "").lower()
    top = min(r["y"] for r in rows)
    span = max(r["y"] + r["h"] for r in rows) - top or 1
    rows = [dict(r, y=round((r["y"] - top) / span, 4)) for r in rows]
    for i, r in enumerate(rows):
        low = r["text"].lower()
        if "store" not in fields and store and store != "unknown" and store.split()[0].lower() in low:
            fields["store"] = {"y": r["y"], "x": r["x"], "row": i}
        for k, test in FIELD_TESTS.items():
            if k not in fields and test(r["text"]):
                fields[k] = {"y": r["y"], "x": r["x"], "row": i}
    item_rows = [i for i, r in enumerate(rows) if any(it["name"] and it["name"][:12] in r["text"] for it in rec["items"])]
    if item_rows:
        fields["items"] = {"y": rows[item_rows[0]]["y"], "y_end": rows[item_rows[-1]]["y"], "rows": len(item_rows)}
    # amount column: right-most text box on rows that end in a price
    money_x = [r["cols"][-1] for r in rows if PRICE_END.search(r["text"]) and len(r["cols"]) > 1]
    n = len(rows)
    multi = sum(1 for r in rows if r["boxes"] >= 3) / n
    colon = sum(1 for r in rows if re.search(r"\w\s*:\s*\S", r["text"])) / n
    prose = sum(1 for r in rows if len(r["text"].split()) >= 8) / n
    boxes = sum(1 for r in rows if re.search(r"\[\s*[xX ]?\s*\]|☐|☑|☒|□", r["text"])) / n
    has_money = rec.get("total") is not None or rec.get("tax") is not None or len(money_x) >= 3
    if has_money and ((aspect or 0) > 1.8 or len(money_x) >= 3):
        kind = "receipt"
    elif boxes > 0.05 or (colon > 0.3 and prose < 0.3):
        kind = "form"
    elif multi > 0.4:
        kind = "table"
    elif prose > 0.3:
        kind = "letter"
    else:
        kind = "document"
    return {"doc_type": kind, "aspect": aspect, "rows": n, "fields": fields, "y_is": "share of the printed text, 0 = first line",
            "amount_column_x": round(statistics.median(money_x), 3) if money_x else None,
            "shape": {"multi_column_rows": round(multi, 2), "label_value_rows": round(colon, 2),
                      "sentence_rows": round(prose, 2), "checkbox_rows": round(boxes, 2)}}


def guess_type_text(rec):
    return "receipt" if rec.get("total") is not None else "document"


def template_path(store):
    return OUT / "templates" / f"{safe(store)}.json"


def header_words(h):
    return {w for w in re.findall(r"[a-z0-9]{3,}", (h or "").lower())}


def match_template(rec):
    """Which known store template this receipt's header (name, address, phone, store #) looks like. 0-100."""
    d = OUT / "templates"
    if not d.is_dir():
        return None, 0
    mine = header_words(rec.get("header")) | header_words(" ".join(str(rec.get(k) or "") for k in ("address", "zip", "phone")))
    best = (None, 0)
    for p in d.glob("*.json"):
        try:
            t = json.loads(p.read_text())
        except ValueError:
            continue
        theirs = set(t.get("header_words", []))
        if not mine or not theirs:
            continue
        score = round(100 * len(mine & theirs) / len(mine | theirs))
        if score > best[1]:
            best = (t, score)
    return best


def use_template(rec, rows):
    """Header match -> store name when it was misread; then fill a missing total from where the store prints it."""
    tpl, score = match_template(rec)
    rec["template_match"] = {"store": tpl["store"], "header_match": score} if tpl else None
    if tpl and score >= 40 and (rec["store"] == "Unknown" or rec["store"] not in [s for _, s, _ in known_stores()]):
        if rec["store"] != tpl["store"]:
            rec["flags"].append(f"store name read as '{rec['store']}', header matches {tpl['store']} ({score}%)")
        rec["store"], rec["category"] = tpl["store"], tpl.get("category") or rec["category"]
    p = template_path(rec["store"])
    if rec["store"] == "Unknown" or not p.exists() or not rows:
        return None
    tpl = json.loads(p.read_text())
    tf = tpl.get("fields", {}).get("total")
    if rec.get("total") is None and tf:
        top = min(r["y"] for r in rows)
        span = max(r["y"] + r["h"] for r in rows) - top or 1
        rows = [dict(r, y=(r["y"] - top) / span) for r in rows]
        near = sorted(rows, key=lambda r: abs(r["y"] - tf["y"]))[:3]
        for r in near:
            v = last_money(r["text"])
            if v is not None and abs(r["y"] - tf["y"]) < 0.04:
                rec["total"] = v
                rec["flags"].append(f"total {v:.2f} taken from where {rec['store']} usually prints it (template)")
                break
    return tpl


def update_template(rec, lay):
    """Running average of where each field sits for this store: the store's standard layout."""
    if rec["store"] == "Unknown" or not lay.get("fields"):
        return None
    p = template_path(rec["store"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tpl = json.loads(p.read_text()) if p.exists() else {"store": rec["store"], "samples": 0, "fields": {}}
    n = tpl["samples"]
    for k, f in lay["fields"].items():
        old = tpl["fields"].get(k)
        if not old:
            tpl["fields"][k] = {"y": f["y"], "x": f.get("x"), "seen": 1}
            continue
        m = old.get("seen", n)
        old["y"] = round((old["y"] * m + f["y"]) / (m + 1), 4)
        if f.get("x") is not None and old.get("x") is not None:
            old["x"] = round((old["x"] * m + f["x"]) / (m + 1), 4)
        old["seen"] = m + 1
    if lay.get("amount_column_x") is not None:
        a = tpl.get("amount_column_x")
        tpl["amount_column_x"] = lay["amount_column_x"] if a is None else round((a * n + lay["amount_column_x"]) / (n + 1), 4)
    hw = set(tpl.get("header_words", [])) | header_words(rec.get("header")) | header_words(
        " ".join(str(rec.get(k) or "") for k in ("address", "zip", "phone")))
    tpl["header_words"] = sorted(hw)[:80]
    for k in ("address", "city", "state", "zip", "phone"):
        if rec.get(k) and not tpl.get(k):
            tpl[k] = rec[k]
    tpl.setdefault("store_numbers", [])
    if rec.get("store_number") and rec["store_number"] not in tpl["store_numbers"]:
        tpl["store_numbers"].append(rec["store_number"])
    if rec.get("_verify_pending") and not tpl.get("verified"):
        tpl["verified"] = rec.pop("_verify_pending")
    tpl.update(samples=n + 1, doc_type=lay["doc_type"], category=rec.get("category"), updated=datetime.now().isoformat(timespec="seconds"))
    p.write_text(json.dumps(tpl, indent=1))
    return tpl


def verify_store(rec):
    """Opt-in (--verify): ask OpenStreetMap (Nominatim, free, no account) whether this store name and address exist
    together. Sends only the store's name, street, city, state and zip. Once per store: the answer is kept in its template."""
    p = template_path(rec["store"])
    tpl = json.loads(p.read_text()) if p.exists() else {}
    if tpl.get("verified") is not None:
        return tpl["verified"]
    if rec["store"] == "Unknown" or not (rec.get("city") or rec.get("zip")):
        return None
    import urllib.parse
    def ask(q):
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": q, "format": "jsonv2", "limit": 5, "addressdetails": 1, "countrycodes": "us"})
        req = urllib.request.Request(url, headers={"User-Agent": f"PAPE-receipts/{VERSION} (local family records tool)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    where = ", ".join(x for x in (rec.get("address"), rec.get("city"), rec.get("state"), rec.get("zip")) if x)
    res = {"checked": datetime.now().isoformat(timespec="seconds"), "source": "OpenStreetMap Nominatim", "query": where}
    try:
        hits = ask(f"{rec['store']}, {rec.get('city') or ''} {rec.get('state') or ''} {rec.get('zip') or ''}")
        time.sleep(1.1)  # Nominatim usage policy: at most 1 request per second
        addr_hits = ask(where) if rec.get("address") else []
    except Exception as e:
        res.update(status="not checked", note=str(e)[:120])
        return res
    house = (re.match(r"\d+", rec.get("address") or "") or [None])[0]
    name_words = set(re.findall(r"[a-z]{3,}", rec["store"].lower()))
    named = [h for h in hits if name_words & set(re.findall(r"[a-z]{3,}", (h.get("name") or h.get("display_name") or "").lower()))]
    same_place = [h for h in named if house and house == (h.get("address") or {}).get("house_number")]
    if same_place:
        res.update(status="verified", note=f"map lists {same_place[0].get('name')} at {same_place[0].get('display_name')}")
    elif named:
        res.update(status="name found nearby", note=named[0].get("display_name"))
    elif addr_hits:
        res.update(status="address exists, store not on the map", note=addr_hits[0].get("display_name"))
    else:
        res.update(status="not found", note="neither the store nor the address was found on the map")
    tpl["verified"] = res
    if p.exists():
        p.write_text(json.dumps(tpl, indent=1))
    else:
        rec["_verify_pending"] = res
    return res


def template_fit(tpl, lay):
    """0-100: how closely this scan's field positions match the store's usual layout."""
    if not tpl or not lay.get("fields"):
        return None
    d = [abs(tpl["fields"][k]["y"] - f["y"]) for k, f in lay["fields"].items() if k in tpl.get("fields", {})]
    return round(max(0.0, 100 * (1 - statistics.mean(d) / 0.1)), 0) if d else None


# ---------- optional local-model check ----------
def model_check(text: str, model: str, rec: dict) -> dict:
    prompt = ("Read this store receipt text from OCR. Reply with JSON only: "
              '{"store":str,"date":"YYYY-MM-DD"|null,"time":"HH:MM"|null,"subtotal":num|null,"tax":num|null,'
              '"total":num|null,"payment":str|null,"items":[{"name":str,"quantity":num,"price":num}]}. '
              "Fix obvious OCR errors in item names. Do not invent items.\n\n" + text[:6000])
    body = json.dumps({"model": model, "stream": False, "think": False, "format": "json",
                       "options": {"temperature": 0}, "messages": [{"role": "user", "content": prompt}]}).encode()
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/chat", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=240) as r:
            got = json.loads(json.loads(r.read())["message"]["content"])
    except Exception as e:  # model missing, Ollama off, bad JSON
        rec["flags"].append(f"local model check skipped: {e}"[:160])
        return rec
    rec["model"] = {"name": model, "answer": got}
    diffs = []
    for k in ("store", "date", "time", "subtotal", "tax", "total", "payment"):
        mv = got.get(k)
        if mv in (None, "", []):
            continue
        if rec.get(k) in (None, "Unknown"):
            rec[k] = mv
        elif str(rec[k]).lower() != str(mv).lower():
            diffs.append(f"{k}: read {rec[k]}, model says {mv}")
    if got.get("items") and len(got["items"]) > len(rec["items"]):
        rec["items_from_model"] = got["items"]
    if diffs:
        rec["flags"].append("model disagrees: " + "; ".join(diffs))
    return rec


# ---------- reconcile item names and places against the store's history ----------
def known_items(store):
    p = OUT / "items.csv"
    if not p.exists():
        return {}
    names = {}
    with open(p, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("store") == store and not (r.get("status") or "").startswith("rescan"):
                names[r["name"]] = names.get(r["name"], 0) + 1
    return names


def reconcile(rec):
    """'XSOAP BAR' -> 'SOAP BAR' when the store has sold 'SOAP BAR' before; 'Anytovvn' -> the template's city.
    The text as read is kept in name_as_read / flags."""
    import difflib
    known = known_items(rec["store"])
    for it in rec["items"]:
        n = it["name"]
        if not known or n in known:
            continue
        cands = [k for k in known if k == n[1:] or k == n[2:]]  # a tax letter glued to the front
        if not cands:
            cands = difflib.get_close_matches(n, list(known), n=1, cutoff=0.88)
        if cands:
            it["name_as_read"], it["name"] = n, cands[0]
    p = template_path(rec["store"])
    if p.exists():
        tpl = json.loads(p.read_text())
        for k in ("city", "address"):
            if tpl.get(k) and rec.get(k) and rec[k] != tpl[k] and \
                    difflib.SequenceMatcher(None, rec[k].lower(), tpl[k].lower()).ratio() >= 0.85:
                rec[k] = tpl[k]
    return rec


# ---------- rescans (same paper scanned again) ----------
def receipt_key(rec):
    """Same receipt = same store, day, minute, total and transaction number, whatever the picture looks like."""
    if rec.get("total") is None:
        return None
    t, store = f"{float(rec['total']):.2f}", safe(rec.get("store")).lower()
    if rec.get("trans_number"):  # transaction numbers are unique per store: survives a misread date
        return "|".join([store, "trans", rec["trans_number"], t])
    if not rec.get("date"):
        return None
    return "|".join([store, rec["date"], rec.get("time") or "", t])


def quality(rec):
    """Higher = clearer read. Used to keep the best of several scans of one receipt."""
    q = 100 - 20 * len([f for f in rec.get("flags", []) if not f.startswith("rescan")])
    check = rec.get("subtotal") if rec.get("subtotal") is not None else (
        rec["total"] - (rec.get("tax") or 0) if rec.get("total") is not None else None)
    if check is not None and rec.get("items") and abs(rec.get("item_sum", 0) - check) <= 0.05:
        q += 15
    if "mirrored" in (rec.get("orientation") or ""):
        q -= 10
    q += 2 * len(rec.get("items", []))
    return q


def set_status(ids_status: dict):
    """Rewrite the status column for some receipts (receipts.csv) and in their receipt.json."""
    p = OUT / "receipts.csv"
    rows = ledger_rows()
    for r in rows:
        if r["receipt_id"] in ids_status:
            r["status"] = ids_status[r["receipt_id"]]
            j = Path(r["folder"]) / "receipt.json"
            if j.exists():
                d = json.loads(j.read_text())
                d["status"] = r["status"]
                j.write_text(json.dumps(d, indent=1, default=str))
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=R_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    ip = OUT / "items.csv"
    if ip.exists():
        with open(ip, newline="") as f:
            items = list(csv.DictReader(f))
        for it in items:
            if it["receipt_id"] in ids_status:
                it["status"] = ids_status[it["receipt_id"]]
        with open(ip, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=I_COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(items)


def settle_rescans(key=None):
    """For every receipt scanned more than once, keep the clearest scan and mark the rest 'rescan of <id>'.
    Returns {receipt_id: status} for the receipts that changed."""
    groups = {}
    for r in ledger_rows():
        k = r.get("receipt_key")
        if k and (key is None or k == key):
            groups.setdefault(k, []).append(r)
    changes = {}
    for k, rs in groups.items():
        if len(rs) < 2:
            continue
        best = max(rs, key=lambda r: (float(r.get("quality") or 0), r.get("read_at") or ""))
        for r in rs:
            want = "" if r is best else f"rescan of {best['receipt_id']}"
            if (r.get("status") or "") != want:
                changes[r["receipt_id"]] = want
    if changes:
        set_status(changes)
    return changes


def counted(rows):
    """Receipts that count in totals: everything except rescans."""
    return [r for r in rows if not (r.get("status") or "").startswith("rescan")]


# ---------- store ----------
def safe(s):
    return re.sub(r"[^A-Za-z0-9]+", "-", s or "unknown").strip("-")[:40] or "unknown"


def ledger_rows():
    p = OUT / "receipts.csv"
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


R_COLS = ["receipt_id", "status", "date", "time", "store", "store_number", "address", "city", "state", "zip", "phone", "email",
          "category", "subtotal", "tax", "total", "payment", "card_last4", "ebt_amount", "item_count", "item_sum",
          "spend_by_category", "doc_type", "orientation", "template_fit", "flags", "read_at", "source_name",
          "source_sha256", "folder", "trans_number", "register", "receipt_key", "quality", "website"]
I_COLS = ["receipt_id", "status", "date", "time", "store", "store_number", "city", "line", "name", "quantity", "each", "price",
          "category", "payment", "card_last4", "name_as_read"]


def append_csv(path: Path, cols, rows):
    if path.exists():
        with open(path, newline="") as f:
            head = next(csv.reader(f), [])
        if head != cols:  # columns changed in a new version: rewrite the file with the new header
            with open(path, newline="") as f:
                old = list(csv.DictReader(f))
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(old)
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def drop_from_ledgers(digest):
    """--redo: forget an earlier read of the same file (ledger rows + its folder) before reading it again."""
    rows = ledger_rows()
    gone = [r for r in rows if r.get("source_sha256") == digest]
    if not gone:
        return
    ids = {r["receipt_id"] for r in gone}
    for name, cols in (("receipts.csv", R_COLS), ("items.csv", I_COLS)):
        p = OUT / name
        if p.exists():
            with open(p, newline="") as f:
                keep = [r for r in csv.DictReader(f) if r.get("receipt_id") not in ids]
            with open(p, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(keep)
    for r in gone:
        if r.get("folder") and Path(r["folder"]).is_dir() and str(OUT) in r["folder"]:
            shutil.rmtree(r["folder"])


def read_one(path: Path, model: str | None, redo: bool = False, verify: bool = False) -> dict:
    path = path.expanduser().resolve()
    if not path.is_file():
        return {"ok": False, "source": str(path), "error": "file not found"}
    if path.suffix.lower() not in IMAGES | {".pdf", ".txt", ".md"}:
        return {"ok": False, "source": str(path), "error": f"not a picture or PDF ({path.suffix})"}
    digest = sha256(path)
    if redo:
        drop_from_ledgers(digest)
    for row in ledger_rows():
        if row.get("source_sha256") == digest:
            j = Path(row["folder"]) / "receipt.json"
            old = json.loads(j.read_text()) if j.exists() else dict(row)
            old.update({"ok": True, "duplicate": True})
            return old
    t0 = time.time()
    work = OUT / ".work" / digest[:12]
    work.mkdir(parents=True, exist_ok=True)
    try:
        text, engine, rows, way, aspect = ocr_file(path, work)
    except subprocess.TimeoutExpired:
        return {"ok": False, "source": str(path), "error": f"reading took over {OCR_TIMEOUT}s, stopped"}
    except FileNotFoundError as e:
        return {"ok": False, "source": str(path), "error": f"missing tool: {e.filename}. Run pape_install_tools.sh"}
    except ValueError as e:
        return {"ok": False, "source": str(path), "error": str(e)}
    rec = parse(text)
    if "mirrored" in way:
        rec["flags"].append("scanned wrong side up: read through the back of the paper. Next time feed it face down")
    tpl = use_template(rec, rows)
    lay = layout_of(rows, rec, aspect)
    if model:
        rec = model_check(text, model, rec)
    rec["layout"] = lay
    rec["orientation"] = way
    rec["template_fit"] = template_fit(tpl, lay)
    rid = f"{rec['date'] or date.today().isoformat()}_{safe(rec['store'])}_{digest[:8]}"
    folder = OUT / (rec["date"] or date.today().isoformat())[:7] / safe(rec["store"]) / rid
    folder.mkdir(parents=True, exist_ok=True)
    original = folder / ("original" + path.suffix.lower())
    shutil.copy2(path, original)
    (folder / "ocr.txt").write_text(text)
    for extra in ("clean.png", "preview.jpg"):
        if (work / extra).exists():
            shutil.move(str(work / extra), folder / extra)
    shutil.rmtree(work, ignore_errors=True)
    if rows:
        with open(folder / "rows.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["page", "row", "text", "x", "y", "w", "h", "conf", "boxes"], extrasaction="ignore")
            w.writeheader()
            w.writerows(dict(r, row=i + 1, page=r.get("page", 1)) for i, r in enumerate(rows))
    update_template(rec, lay)
    reconcile(rec)
    if verify:
        rec["store_check"] = verify_store(rec)
    rec["receipt_key"] = receipt_key(rec)
    rec["quality"] = quality(rec)
    rec.update({"ok": True, "receipt_id": rid, "engine": engine, "seconds": round(time.time() - t0, 1),
                "read_at": datetime.now().isoformat(timespec="seconds"), "source_name": path.name,
                "source": str(path), "source_sha256": digest, "folder": str(folder), "original": str(original),
                "item_count": len(rec["items"]), "doc_type": lay["doc_type"],
                "preview": str(folder / "preview.jpg") if (folder / "preview.jpg").exists() else None, "app": f"I.N-D.O.C.-T.R.I.N. 8-P.I.E.C.E. engine {VERSION}"})
    (folder / "receipt.json").write_text(json.dumps(rec, indent=1, default=str))
    sums = [f"{sha256(f)}  {f.name}" for f in sorted(folder.iterdir()) if f.is_file() and f.name != "SHA256SUMS.txt"]
    (folder / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
    row = dict(rec, flags=" | ".join(rec["flags"]),
               spend_by_category="; ".join(f"{k} {v:.2f}" for k, v in rec["spend_by_category"].items()))
    append_csv(OUT / "receipts.csv", R_COLS, [row])
    append_csv(OUT / "items.csv", I_COLS, [dict(it, receipt_id=rid, status=rec.get("status", ""), date=rec["date"], time=rec["time"], store=rec["store"],
                                               store_number=rec.get("store_number"), city=rec.get("city"), line=n + 1,
                                               payment=rec.get("payment"), card_last4=rec.get("card_last4"))
                                          for n, it in enumerate(rec["items"])])
    if rec["receipt_key"]:
        ch = settle_rescans(rec["receipt_key"])
        if ch:
            mine = ch.get(rid, None)
            if mine:
                rec["status"] = mine
                rec["rescan"] = f"already in the ledger: kept the clearer earlier scan ({mine[10:]})"
            else:
                rec["rescan"] = f"clearer than {len(ch)} earlier scan(s) of this receipt: those are now marked rescan"
    catalog_add(rec)
    with open(OUT / "custody_log.txt", "a") as f:
        f.write(f"{datetime.now().astimezone():%F %T %Z} read {path.name} sha256 {digest} -> {rid} "
                f"({engine}, {rec['words']} words, total {rec['total']})\n")
    return rec


# ---------- store catalog, follow-up jobs, store recon ----------
S_COLS = ["store", "category", "address", "city", "state", "zip", "phone", "email", "website", "store_numbers", "receipts",
          "first_visit", "last_visit", "total_spent", "map_check", "shopify", "locator_url", "recon_at", "recon_note"]


def stores_catalog():
    p = OUT / "stores.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_catalog(cat):
    (OUT / "stores.json").write_text(json.dumps(cat, indent=1))
    with open(OUT / "stores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=S_COLS, extrasaction="ignore")
        w.writeheader()
        for st in sorted(cat.values(), key=lambda x: x["store"]):
            w.writerow(dict(st, store_numbers=" ".join(st.get("store_numbers", [])),
                            map_check=(st.get("map_check") or {}).get("status", "")))


def queue_job(kind, store, **extra):
    q = OUT / "jobs" / "queue.jsonl"
    q.parent.mkdir(parents=True, exist_ok=True)
    for ln in (q.read_text().splitlines() if q.exists() else []):
        j = json.loads(ln)
        if j["kind"] == kind and j["store"] == store and j["status"] == "pending":
            return
    with open(q, "a") as f:
        f.write(json.dumps({"kind": kind, "store": store, "status": "pending",
                            "queued": datetime.now().isoformat(timespec="seconds"), **extra}) + "\n")


def catalog_add(rec):
    """After each receipt: update the store catalog; queue a store-recon job for a new store or a new website."""
    if rec["store"] == "Unknown" or (rec.get("status") or "").startswith("rescan"):
        return
    cat = stores_catalog()
    st = cat.setdefault(rec["store"], {"store": rec["store"], "receipts": 0, "total_spent": 0.0, "store_numbers": []})
    new_site = rec.get("website") and rec["website"] != st.get("website")
    for k in ("category", "address", "city", "state", "zip", "phone", "email", "website"):
        if rec.get(k) and not st.get(k):
            st[k] = rec[k]
    if rec.get("store_number") and rec["store_number"] not in st["store_numbers"]:
        st["store_numbers"].append(rec["store_number"])
    st["receipts"] += 1
    st["total_spent"] = round(st["total_spent"] + float(rec.get("total") or 0), 2)
    if rec.get("date"):
        st["first_visit"] = min(filter(None, [st.get("first_visit"), rec["date"]]))
        st["last_visit"] = max(filter(None, [st.get("last_visit"), rec["date"]]))
    if rec.get("store_check"):
        st["map_check"] = rec["store_check"]
    if st["receipts"] == 1 or new_site:
        queue_job("store_recon", rec["store"], website=st.get("website"))
    save_catalog(cat)


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": f"Mozilla/5.0 PAPE-receipts/{VERSION} (local records)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.geturl(), dict(r.headers), r.read(600_000).decode("utf-8", "replace")


def recon_store(st):
    """One visit to the store's own website: Shopify or not, store-locator page, catalog link. Nothing else is contacted."""
    site = st.get("website")
    if not site:
        return {"recon_note": "no website printed on its receipts yet"}
    url = site if site.startswith("http") else "https://" + site
    try:
        final, headers, html = fetch(url)
    except Exception as e:
        return {"recon_note": f"website did not answer: {str(e)[:80]}"}
    low = html.lower()
    hk = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
    shopify = "x-shopify" in hk or "cdn.shopify.com" in low or "shopify.theme" in low or "myshopify.com" in low
    out = {"website": final.split("//", 1)[-1].rstrip("/"), "shopify": "yes" if shopify else "no"}
    links = re.findall(r'href=["\']([^"\'#]+)["\']', html, re.I)
    loc = next((l for l in links if re.search(r"store-?locator|find-?a-?store|our-?stores|/locations?\b|/stores?\b|/visit", l, re.I)), None)
    if loc:
        out["locator_url"] = urllib.parse.urljoin(final, loc)
    note = [f"site answered at {final}"]
    if shopify:
        time.sleep(1)
        try:
            _, _, pj = fetch(urllib.parse.urljoin(final, "/products.json?limit=250"))
            n = len(json.loads(pj).get("products", []))
            note.append(f"Shopify online catalog: {n} products listed at /products.json")
            out["catalog_url"] = urllib.parse.urljoin(final, "/products.json")
        except Exception:
            note.append("Shopify store; product list not public")
    out["recon_note"] = "; ".join(note)
    return out


def cmd_recon(limit=10):
    """Run pending follow-up jobs (store recon). Only contacts each store's own website, 1 request per second."""
    import urllib.parse  # noqa: F401  (used by recon_store)
    q = OUT / "jobs" / "queue.jsonl"
    jobs = [json.loads(l) for l in q.read_text().splitlines()] if q.exists() else []
    cat = stores_catalog()
    done = []
    for j in jobs:
        if j["status"] != "pending" or len(done) >= limit:
            continue
        st = cat.get(j["store"])
        if not st:
            j["status"] = "skipped"
            continue
        res = recon_store(st)
        st.update(res, recon_at=datetime.now().isoformat(timespec="seconds"))
        j.update(status="done", finished=st["recon_at"], result=res)
        done.append({"store": j["store"], **res})
        time.sleep(1)
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text("".join(json.dumps(j) + "\n" for j in jobs))
    save_catalog(cat)
    emit({"ok": True, "ran": done, "pending": sum(1 for j in jobs if j["status"] == "pending")})


# ---------- scanner ----------
def scanner():
    if not shutil.which("scanimage"):
        return None
    out = run(["scanimage", "-L"], timeout=30)
    m = re.search(r"device `([^']+)'", out)
    return m.group(1) if m else None


def scan_pages(count: int = 0) -> list[Path]:
    dev = scanner()
    if not dev:
        raise RuntimeError("No scanner found. Open the scanner chute and plug the USB cable straight into the Mac.")
    d = OUT / "scans" / datetime.now().strftime("%F_%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    # front side only, gray 300 dpi, auto length for long receipts, deskew + crop in the driver
    opts = ["--source", "ADF Front", "--mode", "Gray", "--resolution", "300"]
    if dev.startswith("fujitsu"):
        opts += ["--ald=yes", "--swdeskew=yes", "--swcrop=yes"]
    if count:
        opts.append(f"--batch-count={count}")
    p = subprocess.run(["scanimage", "-d", dev, *opts, "--format=tiff", f"--batch={d}/receipt_%03d.tif"],
                       capture_output=True, text=True, timeout=600)
    pages = sorted(d.glob("receipt_*.tif"))
    msg = (p.stderr or "").lower()
    if not pages:
        if "jam" in msg:
            raise RuntimeError("The feeder is jammed. Open the scanner lid, take the paper out, smooth it, and try again. "
                               "Take any weight off the stack: it can stop the rollers pulling one sheet.")
        if "cover" in msg or "open" in msg:
            raise RuntimeError("The scanner lid or chute is open or not latched. Close it and try again.")
        raise RuntimeError("0 pages. Put receipts face down, top edge first, then press Scan again.")
    return pages


# ---------- commands ----------
def cmd_check():
    tools = {t: bool(shutil.which(t)) for t in ("tesseract", "pdftotext", "pdftoppm", "scanimage", "sips")}
    ollama = []
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            ollama = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        pass
    rows = ledger_rows()
    emit({"ok": True, "version": VERSION, "out": str(OUT), "inbox": str(OUT / "inbox"), "tools": tools,
          "scanner": scanner() if tools["scanimage"] else None,
          "best_ocr": "RapidOCR" if rapid() else "Tesseract only (install the P.A.P.E. venv for better receipts)", "models": ollama, "receipts": len(rows)})


def cmd_dedupe():
    """Fill fingerprints for older rows, then mark rescans across the whole ledger."""
    rows = ledger_rows()
    for r in rows:
        j = Path(r["folder"]) / "receipt.json"
        if j.exists():
            d = json.loads(j.read_text())
            if not d.get("trans_number"):
                txt = (Path(r["folder"]) / "ocr.txt").read_text() if (Path(r["folder"]) / "ocr.txt").exists() else ""
                m = re.search(r"TRANS(?:ACTION)?\.?\s*-?\s*(?:#|NO\.?|NUM(?:BER)?)?\s*:?\s*(\d{3,})", txt.upper())
                d["trans_number"] = m.group(1) if m else None
            d["receipt_key"], d["quality"] = receipt_key(d), quality(d)
            j.write_text(json.dumps(d, indent=1, default=str))
            r.update(trans_number=d["trans_number"], receipt_key=d["receipt_key"], quality=d["quality"])
    with open(OUT / "receipts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=R_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    ch = settle_rescans()
    statuses = {r["receipt_id"]: r.get("status") or "" for r in ledger_rows()}
    set_status(statuses)
    # reconcile names/cities of rescans against the counted receipts
    for r in ledger_rows():
        if not statuses.get(r["receipt_id"]):
            continue
        j = Path(r["folder"]) / "receipt.json"
        if not j.exists():
            continue
        d = reconcile(json.loads(j.read_text()))
        j.write_text(json.dumps(d, indent=1, default=str))
        fix = {it.get("name_as_read"): it["name"] for it in d["items"] if it.get("name_as_read")}
        ip = OUT / "items.csv"
        with open(ip, newline="") as f:
            items = list(csv.DictReader(f))
        for it in items:
            if it["receipt_id"] == r["receipt_id"]:
                if it["name"] in fix:
                    it["name_as_read"], it["name"] = it["name"], fix[it["name"]]
                it["city"] = d.get("city") or it.get("city")
        with open(ip, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=I_COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(items)
        r["city"] = d.get("city") or r.get("city")
    rows2 = ledger_rows()
    for r in rows2:
        j = Path(r["folder"]) / "receipt.json"
        if j.exists():
            r["city"] = json.loads(j.read_text()).get("city") or r.get("city")
    with open(OUT / "receipts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=R_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows2)
    old_cat = stores_catalog()
    (OUT / "stores.json").unlink(missing_ok=True)
    for r in counted(ledger_rows()):
        j = Path(r["folder"]) / "receipt.json"
        if j.exists():
            d = json.loads(j.read_text())
            if not d.get("website"):
                txt = (Path(r["folder"]) / "ocr.txt").read_text() if (Path(r["folder"]) / "ocr.txt").exists() else ""
                d["website"] = parse(txt).get("website") if txt else None
            catalog_add(d)
    cat = stores_catalog()
    for k, v in old_cat.items():  # keep earlier recon / map results
        if k in cat:
            for f in ("map_check", "shopify", "locator_url", "catalog_url", "recon_at", "recon_note"):
                if v.get(f) and not cat[k].get(f):
                    cat[k][f] = v[f]
    save_catalog(cat)
    emit({"ok": True, "receipts": len(rows), "marked": ch, "counted": len(counted(ledger_rows())), "stores": len(cat)})


def cmd_report():
    """Totals for an audit: by month x category, by store, by card. Written to <out>/reports/ and printed."""
    items_p = OUT / "items.csv"
    all_rows = ledger_rows()
    rows = counted(all_rows)
    keep = {r["receipt_id"] for r in rows}
    items = [i for i in (list(csv.DictReader(open(items_p, newline=""))) if items_p.exists() else []) if i["receipt_id"] in keep]
    f = lambda v: float(v) if v not in (None, "") else 0.0
    def table(keyfn, src, amount):
        t = {}
        for r in src:
            k = keyfn(r)
            c = t.setdefault(k, {"receipts": set(), "amount": 0.0})
            c["receipts"].add(r.get("receipt_id"))
            c["amount"] += f(r.get(amount))
        return [dict(zip(("month", "group"), k), receipts=len(v["receipts"]), amount=round(v["amount"], 2))
                for k, v in sorted(t.items())]
    out = {
        "by_month_category": table(lambda r: ((r.get("date") or "")[:7], r.get("category") or "other"), items, "price"),
        "by_month_store": table(lambda r: ((r.get("date") or "")[:7], f"{r.get('store')} #{r.get('store_number') or '?'}"), rows, "total"),
        "by_month_card": table(lambda r: ((r.get("date") or "")[:7], r.get("card_last4") or "unknown"), rows, "total"),
    }
    d = OUT / "reports"
    d.mkdir(exist_ok=True)
    for name, data in out.items():
        with open(d / f"{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["month", "group", "receipts", "amount"])
            w.writeheader()
            w.writerows(data)
    grand = round(sum(f(r.get("total")) for r in rows), 2)
    emit({"ok": True, "receipts": len(rows), "rescans_left_out": len(all_rows) - len(rows), "items": len(items),
          "grand_total": grand, "folder": str(d), **out})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "read", "scan", "inbox", "ledger", "report", "dedupe", "recon", "stores"])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--model", default=None, help="local Ollama model to double-check each receipt, e.g. gemma4:12b")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--verify", action="store_true", help="check NEW stores once on OpenStreetMap (sends store name + address)")
    ap.add_argument("--redo", action="store_true", help="read again even if this file was read before (replaces the old rows)")
    ap.add_argument("--count", type=int, default=0, help="scan: stop after this many receipts (0 = whole stack)")
    a = ap.parse_args()
    background()
    if a.command == "check":
        return cmd_check()
    if a.command == "report":
        return cmd_report()
    if a.command == "recon":
        with Lock():
            return cmd_recon()
    if a.command == "stores":
        cat = stores_catalog()
        return emit({"ok": True, "stores": list(cat.values()), "csv": str(OUT / "stores.csv")})
    if a.command == "dedupe":
        with Lock():
            return cmd_dedupe()
    if a.command == "ledger":
        rows = ledger_rows()[-a.limit:][::-1]
        return emit({"ok": True, "out": str(OUT), "count": len(ledger_rows()), "receipts": rows})
    with Lock():
        if a.command == "scan":
            try:
                files = scan_pages(a.count)
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                return emit({"ok": False, "error": str(e), "results": []})
        elif a.command == "inbox":
            inbox = OUT / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            files = sorted(p for p in inbox.iterdir() if p.is_file() and not p.name.startswith("."))
        else:
            files = [Path(f) for f in a.files]
        results = [read_one(f, a.model, a.redo, a.verify) for f in files]
        if a.command == "inbox":
            done = OUT / "inbox" / "done"
            done.mkdir(exist_ok=True)
            for f, r in zip(files, results):
                if r.get("ok"):
                    shutil.move(str(f), done / f.name)
        emit({"ok": True, "out": str(OUT), "results": results})


if __name__ == "__main__":
    main()
