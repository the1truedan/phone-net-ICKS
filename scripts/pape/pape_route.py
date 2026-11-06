#!/usr/bin/env python3
"""P.A.P.E.R. (Paper Accessibility, Parsing & Evidence Router): "What I'd use", per page. Cheapest tool that is good enough; escalate only when needed.

    ~/models/pape_tools/.venv/bin/python scripts/pape_route.py <pdf> [--profile laptop|mac|full] [--out DIR]

Per page (features first, then tools):
  probe     text layer chars (pdftotext) + ada-doc-check needs_ocr (repo: ada-doc-check)
  digital   page has a text layer  -> text as-is; tables via pdfplumber (exact, ~0.1 s)
  scan      no text layer          -> Tesseract + RapidOCR (both CPU); their word agreement decides:
              agree >= 0.90        -> Tesseract text is accepted
              agree <  0.90        -> escalate: PaddleOCR-VL 1.6 (local GGUF, Mac SSD, ~9 s/page)   [profile mac/full]
            table check on scans   -> img2table (ruled tables); a column-aligned grid without rules is flagged
              table flagged        -> PaddleOCR-VL "Table Recognition:" [mac/full]; Unlimited-OCR-2 on a CUDA GPU host [full, queued]
  laptop profile = Tesseract + RapidOCR only (old Windows/WSL machine). Never loads models over the network.
Writes DIR/route.json (per page: features, route, reasons, seconds), DIR/page_NNN.txt, DIR/tables/*.csv.
Prints counts and timings only (family documents: no page text on screen).
"""
import argparse, csv, json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/ada-doc-check"))
GGUF = os.path.expanduser("~/models/pape_ocr/PaddlePaddle__PaddleOCR-VL-1.6-GGUF")
AGREE_OK = 0.90
ORDER_OK = 0.80  # reading order: below this the page is re-read by a layout-aware model


def words(t):
    return re.findall(r"[a-z0-9]+", t.lower())


def agree(a, b):
    from collections import Counter
    wa, wb = Counter(words(a)), Counter(words(b))
    n = sum((wa & wb).values())
    return (n / max(1, sum(wa.values())) + n / max(1, sum(wb.values()))) / 2


def order_agree(a, b):
    """Reading-order agreement: sequence similarity of the two word streams (catches column mix-ups bag-of-words misses)."""
    import difflib
    wa, wb = words(a)[:1500], words(b)[:1500]
    return difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio() if wa and wb else 0.0


def page_text(pdf, i):
    return subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), pdf, "-"], capture_output=True, text=True).stdout


def render(pdf, i, d):
    stem = f"{d}/p{i:03d}"
    subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile", "-f", str(i), "-l", str(i), pdf, stem], check=True)
    return stem + ".png"


def tesseract(img):
    return subprocess.run(["tesseract", img, "-", "-l", "eng", "--psm", "3"], capture_output=True, text=True).stdout


def rapid(img):
    from rapidocr import RapidOCR
    r = RapidOCR(params={"EngineConfig.onnxruntime.intra_op_num_threads": 4})(img)
    return "\n".join(r.txts or [])


def paddle(img, prompt="OCR:"):
    r = subprocess.run(["llama-mtmd-cli", "-m", f"{GGUF}/PaddleOCR-VL-1.6-GGUF.gguf", "--mmproj", f"{GGUF}/PaddleOCR-VL-1.6-GGUF-mmproj.gguf",
                        "--image", img, "-p", prompt, "--temp", "0", "-n", "3000", "-c", "8192", "--jinja"],
                       capture_output=True, text=True, timeout=600)
    return r.stdout if r.returncode == 0 else ""


def grid_flag(img):
    """Column-aligned grid without ruled lines: Tesseract TSV word lefts clustering into >= 3 stable columns over >= 5 lines."""
    tsv = subprocess.run(["tesseract", img, "-", "--psm", "6", "tsv"], capture_output=True, text=True).stdout.splitlines()[1:]
    from collections import Counter, defaultdict
    lines = defaultdict(list)
    for row in tsv:
        f = row.split("\t")
        if len(f) == 12 and f[11].strip() and f[0] == "5":
            lines[(f[2], f[3], f[4])].append(int(f[6]) // 40)
    starts = Counter(x for v in lines.values() if len(v) >= 3 for x in set(v))
    cols = [c for c, n in starts.items() if n >= 5]
    return len(cols) >= 3


OCR_CREATOR = re.compile(r"ocrmypdf|tesseract|abbyy|finereader|readiris|camscanner|scansnap|intsig|adobe scan|genius scan", re.I)


def full_page_image(pdf, i):
    """True when one image covers >= 85% of the page (a scan, whatever text layer sits on top)."""
    info = subprocess.run(["pdfinfo", "-f", str(i), "-l", str(i), pdf], capture_output=True, text=True).stdout
    m = re.search(rf"Page\s+{i} size:\s+([\d.]+) x ([\d.]+)", info) or re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", info)
    if not m:
        return False
    pw, ph = float(m.group(1)), float(m.group(2))
    for line in subprocess.run(["pdfimages", "-list", "-f", str(i), "-l", str(i), pdf], capture_output=True, text=True).stdout.splitlines()[2:]:
        f = line.split()
        try:
            w, h, xppi, yppi = int(f[3]), int(f[4]), float(f[12]), float(f[13])
        except (IndexError, ValueError):
            continue
        if xppi and yppi and (w / xppi * 72) * (h / yppi * 72) >= 0.85 * pw * ph:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("--profile", choices=["laptop", "mac", "full"], default="mac")
    ap.add_argument("--out")
    a = ap.parse_args()
    out = a.out or re.sub(r"\.pdf$", "", a.pdf, flags=re.I) + ".route"
    os.makedirs(f"{out}/tables", exist_ok=True)
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", a.pdf], capture_output=True, text=True).stdout).group(1))
    plan = {"pdf": a.pdf, "profile": a.profile, "pages": []}
    creator = subprocess.run(["pdfinfo", a.pdf], capture_output=True, text=True).stdout
    try:
        from ada_check.triage import needs_ocr
        tri = needs_ocr(a.pdf, text="".join(page_text(a.pdf, i) for i in range(1, n + 1)))
        plan["ada_doc_check"] = {k: tri.get(k) for k in ("decidable", "needs_ocr", "accessible_as_is", "chars")}
    except Exception as e:
        plan["ada_doc_check"] = {"error": e.__class__.__name__}
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, n + 1):
            t0 = time.time(); pg = {"page": i, "reasons": []}
            layer = page_text(a.pdf, i)
            fonts = subprocess.run(["pdffonts", "-f", str(i), "-l", str(i), a.pdf], capture_output=True, text=True).stdout
            ocr_layer = "GlyphLessFont" in fonts or full_page_image(a.pdf, i) or bool(OCR_CREATOR.search(creator))
            if ocr_layer:
                pg["reasons"].append("text layer is OCR over a scanned image: re-checked like a scan")
            if len(layer.strip()) >= 80 and not ocr_layer:
                pg["route"], text = "digital: text layer", layer
                try:
                    import pdfplumber
                    with pdfplumber.open(a.pdf) as p:
                        tabs = p.pages[i - 1].extract_tables()
                    for k, tb in enumerate(tabs):
                        with open(f"{out}/tables/p{i:03d}_t{k + 1}_pdfplumber.csv", "w", newline="") as fh:
                            csv.writer(fh).writerows(tb)
                    pg["tables"] = [f"{len(tb)}x{max((len(r) for r in tb), default=0)}" for tb in tabs]
                    pg["reasons"].append(f"{len(layer.strip())} chars in text layer; pdfplumber tables {pg['tables']}")
                except Exception as e:
                    pg["reasons"].append(f"pdfplumber {e.__class__.__name__}")
            else:
                img = render(a.pdf, i, tmp)
                te = layer if (ocr_layer and len(layer.strip()) >= 80) else tesseract(img)
                ra = rapid(img)
                ag = agree(te, ra); og = order_agree(te, ra)
                pg["agree_tesseract_rapidocr"], pg["order_agree"] = round(ag, 3), round(og, 3)
                text = te; pg["route"] = "scan: tesseract (rapidocr agrees)"
                if ag < AGREE_OK or og < ORDER_OK:
                    pg["reasons"].append(f"engines agree on words {ag:.2f} / on reading order {og:.2f} (need {AGREE_OK} / {ORDER_OK})")
                    if a.profile != "laptop":
                        pv = paddle(img)
                        if pv.strip():
                            text, pg["route"] = pv, "scan: escalated to PaddleOCR-VL"
                    else:
                        pg["route"] = "scan: tesseract (low agreement, laptop profile: flagged for review)"
                if grid_flag(img):
                    pg["table_flag"] = True
                    pg["reasons"].append("column-aligned grid without rules")
                    if a.profile != "laptop":
                        tv = paddle(img, "Table Recognition:")
                        if tv.strip():
                            open(f"{out}/tables/p{i:03d}_paddleocr_vl_table.md", "w").write(tv)
                            pg["reasons"].append("PaddleOCR-VL table pass written")
                    if a.profile == "full":
                        pg["queue_gpu"] = "unlimited-ocr-2 (real HTML tables)"
            open(f"{out}/page_{i:03d}.txt", "w").write(text)
            pg["words"] = len(words(text)); pg["secs"] = round(time.time() - t0, 1)
            plan["pages"].append(pg)
            print(f"p{i:03d} {pg['secs']:6.1f}s  {pg['route']:<52} words={pg['words']:<5} {('agree=%.2f order=%.2f' % (pg['agree_tesseract_rapidocr'], pg['order_agree'])) if 'agree_tesseract_rapidocr' in pg else ''} {'TABLE' if pg.get('table_flag') or pg.get('tables') else ''}", flush=True)
    json.dump(plan, open(f"{out}/route.json", "w"), indent=1)
    from collections import Counter
    print(json.dumps({"ada_doc_check": plan["ada_doc_check"], "routes": Counter(p["route"] for p in plan["pages"]),
                      "seconds": round(sum(p["secs"] for p in plan["pages"]), 1)}, default=str))
    print(out)


if __name__ == "__main__":
    main()
