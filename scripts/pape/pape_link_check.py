#!/usr/bin/env python3
"""P.A.P.E. link check: every link on a set of pages -> status, final address, redirect off-site, login wall, soft 404.

    python3 scripts/pape_link_check.py PAGES.txt --out DIR      # one page URL per line

Writes DIR/LINKS.tsv (one row per unique link) and DIR/LINK_REPORT.md (broken, misdirected and login-gated links,
with the pages that carry them). Never drops a broken link: it is listed with the exact error and the check time.
"""
import argparse, concurrent.futures as cf, datetime, html.parser, os, re, ssl, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh) P.A.P.E.-link-check"
LOGIN = re.compile(r"login\.microsoftonline|sharepoint\.com|/login|/signin|sign-in|okta\.com|auth0|/sso/|accounts\.google", re.I)
SOFT404 = re.compile(r"page not found|404|no longer available|cannot be found|doesn.t exist", re.I)


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.out = []; self._a = None; self._t = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._a = dict(attrs).get("href"); self._t = ""

    def handle_data(self, d):
        if self._a is not None:
            self._t += d

    def handle_endtag(self, tag):
        if tag == "a" and self._a:
            self.out.append((self._a, " ".join(self._t.split())[:80]))
        if tag == "a":
            self._a = None


def get(url, method="GET", limit=200_000):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        body = r.read(limit) if method == "GET" else b""
        return r.status, r.geturl(), r.headers.get("Content-Type", ""), body


def check(url):
    try:
        st, final, ctype, body = get(url)
        title = re.search(rb"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        title = title.group(1).decode("utf-8", "replace").strip()[:80] if title else ""
        return st, final, ctype.split(";")[0], title, ""
    except urllib.error.HTTPError as e:
        return e.code, e.geturl() or url, "", "", f"HTTP {e.code} {e.reason}"
    except Exception as e:
        return 0, url, "", "", f"{type(e).__name__}: {str(e)[:120]}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("pages"); ap.add_argument("--out", required=True); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    pages = [l.strip() for l in open(a.pages) if l.strip() and not l.startswith("#")]
    found = {}  # link -> (text, [pages])
    for p in pages:
        try:
            _, final, _, body = get(p, limit=3_000_000)
        except Exception as e:
            found.setdefault(p, ("(page itself)", []))[1].append("(start list)"); continue
        lp = Links(); lp.feed(body.decode("utf-8", "replace"))
        for href, text in lp.out:
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            u = urllib.parse.urljoin(final, href).split("#")[0]
            found.setdefault(u, (text, []))[1].append(p)
    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(zip(found, ex.map(check, found)))
    rows = []
    for u, (text, on) in found.items():
        st, final, ctype, title, err = res[u]
        src = urllib.parse.urlparse(u).netloc.replace("www.", ""); dst = urllib.parse.urlparse(final).netloc.replace("www.", "")
        flags = []
        if err or st >= 400: flags.append("BROKEN")
        if "html" in ctype and SOFT404.search(title or ""): flags.append("SOFT404")
        if final.rstrip("/") != u.rstrip("/") and dst != src: flags.append(f"REDIRECT_OFFSITE->{dst}")
        if LOGIN.search(final) and not LOGIN.search(u): flags.append("LOGIN_WALL")
        elif LOGIN.search(final): flags.append("LOGIN_SITE")
        rows.append((u, text, st, final, ctype, title, err, ",".join(flags), len(on), on[0]))
    with open(f"{a.out}/LINKS.tsv", "w") as f:
        f.write("link\ttext\tstatus\tfinal\ttype\ttitle\terror\tflags\tpages\tfirst_page\n")
        for r in sorted(rows, key=lambda r: (not r[7], r[0])):
            f.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")
    bad = [r for r in rows if r[7]]
    L = [f"# Link check ({now})", "", f"{len(pages)} pages · {len(rows)} unique links · **{len(bad)} flagged**", "",
         "| Flag | Link text | Link | Status / error | Ends at | On page |", "|---|---|---|---|---|---|"]
    for r in sorted(bad, key=lambda r: r[7]):
        L.append(f"| {r[7]} | {r[1] or '—'} | {r[0]} | {r[6] or r[2]} | {r[3] if r[3] != r[0] else '—'} | {r[9]} |")
    open(f"{a.out}/LINK_REPORT.md", "w").write("\n".join(L) + "\n")
    print(f"{len(rows)} links, {len(bad)} flagged -> {a.out}/LINK_REPORT.md")


if __name__ == "__main__":
    main()
