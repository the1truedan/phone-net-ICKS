#!/usr/bin/env python3
"""Basic checks on a raw genotype file (23andMe format). Standard library only.

  python3 -I dna_basic.py raw.txt out_dir

Writes basic.json: SNP counts, call rate, heterozygosity per chromosome,
X heterozygosity (sex check), Y and MT call counts, and runs of homozygosity (ROH:
long stretches with no heterozygous SNP, >= 3 Mb and >= 200 SNPs).
"""
import json, sys
from collections import defaultdict
from pathlib import Path


def main(src, out):
    chrom = defaultdict(lambda: {"n": 0, "called": 0, "het": 0, "pos": [], "hetflag": []})
    for line in open(src):
        if line.startswith("#") or not line.strip():
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 4 or not f[2].isdigit():
            continue
        rs, c, p, g = f[:4]
        d = chrom[c]
        d["n"] += 1
        if g in ("--", "00", "") or "-" in g or "0" in g:
            continue
        d["called"] += 1
        het = len(g) == 2 and g[0] != g[1]
        d["het"] += het
        if c not in ("X", "Y", "MT", "XY"):
            d["pos"].append(int(p))
            d["hetflag"].append(het)
    res = {"chrom": {}, "roh": []}
    for c, d in chrom.items():
        res["chrom"][c] = {"snps": d["n"], "called": d["called"], "het": d["het"],
                           "het_rate": round(d["het"] / d["called"], 4) if d["called"] else None}
        if d["pos"]:
            order = sorted(zip(d["pos"], d["hetflag"]))
            start, cnt = None, 0
            for i, (p, h) in enumerate(order + [(10**10, True)]):
                if not h:
                    if start is None:
                        start, cnt = p, 0
                    cnt += 1
                    last = p
                else:
                    if start is not None and cnt >= 200 and last - start >= 3_000_000:
                        res["roh"].append({"chrom": c, "start": start, "end": last, "mb": round((last - start) / 1e6, 2), "snps": cnt})
                    start = None
    tot = sum(v["snps"] for v in res["chrom"].values())
    called = sum(v["called"] for v in res["chrom"].values())
    res["total_snps"], res["called"], res["call_rate"] = tot, called, round(called / tot, 4)
    res["roh_total_mb"] = round(sum(r["mb"] for r in res["roh"]), 1)
    Path(out, "basic.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("total_snps", "called", "call_rate", "roh_total_mb")}))
    for c in ("X", "Y", "MT"):
        print(c, res["chrom"].get(c))
    print("ROH:", [(r["chrom"], r["mb"]) for r in sorted(res["roh"], key=lambda r: -r["mb"])][:15])


if __name__ == "__main__":
    main(*sys.argv[1:3])
