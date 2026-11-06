#!/usr/bin/env python3
"""P.A.P.E. version diff: what changed between two versions of an official document, and what kind of change it is.

    python3 scripts/pape_version_diff.py OLD.pdf NEW.pdf --out REPORT.md [--max-hunks 40] [--model gemma4:12b]

1. text of both (pdftotext), split into sentences, normalized (whitespace, hyphenation, page furniture)
2. difflib on the sentence lists -> changed hunks (deleted / added / replaced), tiny or numbering-only hunks dropped
3. local LLM (Ollama on this Mac, thinking off, JSON schema) labels each hunk:
     policy | protocol | procedure | best_practice | eligibility_or_coverage | contacts_or_dates | wording_only
   with a one-line plain-language summary
4. Markdown: before ~~struck~~ / after **bold**, grouped by kind, biggest kinds first. Quotes are capped at 40 words.
Public documents only (the text goes into the report). Local model only.
"""
import argparse, difflib, json, re, subprocess, time, urllib.request

KINDS = ["policy", "protocol", "procedure", "best_practice", "eligibility_or_coverage", "contacts_or_dates", "wording_only"]
SCHEMA = {"type": "object", "required": ["kind", "summary"], "properties": {
    "kind": {"type": "string", "enum": KINDS}, "summary": {"type": "string"}}}


def sentences(pdf):
    t = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
    t = re.sub(r"-\n(?=[a-z])", "", t)                      # re-join hyphenated words
    t = re.sub(r"(?m)^\s*(page\s*)?\d+\s*$", " ", t, flags=re.I)  # page numbers
    t = re.sub(r"\s+", " ", t)
    out = [s.strip() for s in re.split(r"(?<=[.!?;:])\s+(?=[A-Z0-9•(])", t) if len(s.strip()) > 3]
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def hunks(a, b):
    sm = difflib.SequenceMatcher(None, [norm(x) for x in a], [norm(x) for x in b], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        old, new = " ".join(a[i1:i2]), " ".join(b[j1:j2])
        if difflib.SequenceMatcher(None, norm(old), norm(new)).ratio() > 0.97:
            continue  # spacing / punctuation only
        if len(norm(old)) + len(norm(new)) < 25 or re.fullmatch(r"[\d\s.]*", norm(old) + norm(new)):
            continue
        if (old + new).count(". . .") >= 3 or re.search(r"\.{6,}", old + new):
            continue  # table of contents / dot leaders
        yield {"op": op, "old": old, "new": new, "at_old": i1, "at_new": j1}


def label(h, model):
    prompt = ("A government document about family caregiving / long-term care / hospice was revised. Below is one change.\n"
              "Classify it: policy (rules, rights, obligations), protocol (required steps or standards of care), procedure "
              "(how to apply, forms, process), best_practice (recommended practice, guidance), eligibility_or_coverage, "
              "contacts_or_dates (names, phone, URLs, dates, years), wording_only (same meaning). wording_only is ONLY for "
              "pure rephrasing: if the change adds or removes a group of people, a right, a requirement, a step, a program, a "
              "reason or a commitment, or changes who it applies to, it is NOT wording_only. When unsure, prefer policy. "
              "Then one plain-language sentence saying what changed for a caregiver.\n\n"
              f"BEFORE: {h['old'][:1500] or '(nothing: this text was added)'}\nAFTER: {h['new'][:1500] or '(nothing: this text was removed)'}\n")
    body = {"model": model, "prompt": prompt, "stream": False, "think": False, "format": SCHEMA,
            "options": {"temperature": 0, "num_ctx": 4096}, "keep_alive": "10m"}
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        return json.loads(json.load(urllib.request.urlopen(req, timeout=180)).get("response") or "{}")
    except Exception as e:
        return {"kind": "unlabeled", "summary": f"(model unavailable: {e.__class__.__name__})"}


def cap(s, n=40):
    w = s.split()
    return " ".join(w[:n]) + (" …" if len(w) > n else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("--out", required=True)
    ap.add_argument("--max-hunks", type=int, default=40); ap.add_argument("--model", default="gemma4:12b")
    ap.add_argument("--old-label", default="older version"); ap.add_argument("--new-label", default="newer version")
    a = ap.parse_args()
    A, B = sentences(a.old), sentences(a.new)
    H = list(hunks(A, B))
    H.sort(key=lambda h: -(len(h["old"]) + len(h["new"])))
    picked = H[: a.max_hunks]
    t0 = time.time()
    for h in picked:
        h.update(label(h, a.model))
    picked.sort(key=lambda h: (h["at_new"], h["at_old"]))
    from collections import Counter
    kinds = Counter(h.get("kind") for h in picked)
    sim = difflib.SequenceMatcher(None, [norm(x) for x in A], [norm(x) for x in B], autojunk=False).ratio()
    L = [f"# Version diff: {a.old_label} → {a.new_label}", "",
         f"Sentences: {len(A)} → {len(B)} · overall sentence similarity {sim:.0%} · changed passages {len(H)} "
         f"(top {len(picked)} by size labeled by local {a.model} in {time.time() - t0:.0f} s)", "",
         "| Kind of change | Count |", "|---|---:|"] + [f"| {k} | {n} |" for k, n in kinds.most_common()]
    order = [k for k in KINDS if k != "wording_only"] + ["wording_only", "unlabeled"]
    for k in order:
        hs = [h for h in picked if h.get("kind") == k]
        if not hs:
            continue
        L += ["", f"## {k.replace('_', ' ').title()} ({len(hs)})", ""]
        for h in hs:
            L.append(f"- **{h.get('summary', '').strip()}**")
            if h["old"]:
                L.append(f"  - before: ~~{cap(h['old'])}~~")
            if h["new"]:
                L.append(f"  - after: **{cap(h['new'])}**")
    L += ["", "Labels come from a local model and are a first pass for a human reader; the quotes are the evidence."]
    open(a.out, "w").write("\n".join(L) + "\n")
    print(json.dumps({"sentences": [len(A), len(B)], "similarity": round(sim, 3), "changed": len(H), "kinds": kinds}, default=str))
    print(a.out)


if __name__ == "__main__":
    main()
