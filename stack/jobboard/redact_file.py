#!/usr/bin/env python3
"""Make a blocked-out (█) copy of a local report for sharing, using the job board's redactor.

    python3 stack/jobboard/redact_file.py INPUT.html OUTPUT.html [--terms config/redact.txt]

Terms: one per line in a git-ignored file (prefix cs: for case-sensitive). Built-in patterns also cover phone numbers,
emails, street addresses, SSNs, long digit runs and absolute local paths. Only visible text is changed. Always read the
output before publishing it: a term list can't know a name you didn't put in it.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jobboard import Redactor  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("input"); ap.add_argument("output")
ap.add_argument("--terms", default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "redact.txt"))
a = ap.parse_args()
text = open(a.input, errors="ignore").read()
out = Redactor(a.terms)(text)
open(a.output, "w").write(out)
print(f"wrote {a.output}  ({out.count(chr(9608))} characters blocked)")
