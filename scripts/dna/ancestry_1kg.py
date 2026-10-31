#!/usr/bin/env python3
"""Rough ancestry check against 1000 Genomes population frequencies (Ensembl REST).

  python ancestry_1kg.py raw.txt out_dir [n_snps]

1. Picks n random autosomal SNPs from the raw file (no A/T or C/G SNPs).
2. Sends ONLY the rsIDs to Ensembl (public); gets 1000 Genomes phase 3 allele
   frequencies for 26 populations. Genotypes never leave this machine.
3. Scores the genotypes locally:
   - log-likelihood for each population (as if 100% from it), ranked;
   - supervised admixture (EM) over a reference set of populations.
Writes freqs.jsonl (cache), ancestry.json.
"""
import json, random, sys, time, urllib.request
from pathlib import Path
import numpy as np

POPS = ["GBR", "CEU", "FIN", "IBS", "TSI", "YRI", "LWK", "ESN", "MSL", "GWD", "ASW", "ACB",
        "CHB", "JPT", "CHS", "CDX", "KHV", "GIH", "PJL", "BEB", "STU", "ITU", "MXL", "PUR", "CLM", "PEL"]
MIX = ["GBR", "CEU", "FIN", "IBS", "TSI", "YRI", "CHB", "GIH", "PEL"]
URL = "https://rest.ensembl.org/variation/homo_sapiens?pops=1"
PAL = {frozenset("AT"), frozenset("CG")}


def fetch(ids):
    req = urllib.request.Request(URL, data=json.dumps({"ids": ids}).encode(), headers={"Content-Type": "application/json", "Accept": "application/json"})
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(3 + 3 * i)
    return {}


def main(raw, out, n=3000):
    out = Path(out)
    random.seed(1030)
    geno = {}
    for line in open(raw):
        f = line.rstrip("\n").split("\t")
        if len(f) >= 4 and f[0].startswith("rs") and f[1].isdigit() and len(f[3]) == 2 and set(f[3]) <= set("ACGT"):
            geno[f[0]] = f[3]
    pick = random.sample(sorted(geno), min(int(n), len(geno)))
    cache = out / "freqs.jsonl"
    have = {}
    if cache.exists():
        for l in open(cache):
            x = json.loads(l); have[x["rs"]] = x
    todo = [r for r in pick if r not in have]
    from concurrent.futures import ThreadPoolExecutor
    chunks = [todo[i:i + 50] for i in range(0, len(todo), 50)]

    def conv(res):
        out = []
        for rs, v in res.items():
            fr = {}
            for p in v.get("populations", []):
                name = p.get("population", "")
                if name.startswith("1000GENOMES:phase_3:") and name.split(":")[-1] in POPS:
                    fr.setdefault(name.split(":")[-1], {})[p["allele"]] = p["frequency"]
            out.append({"rs": rs, "fr": fr})
        return out

    with open(cache, "a") as fh, ThreadPoolExecutor(4) as ex:
        for k, res in enumerate(ex.map(fetch, chunks)):
            for rec in conv(res):
                fh.write(json.dumps(rec) + "\n"); have[rec["rs"]] = rec
            fh.flush()
            print("chunk", k + 1, "/", len(chunks), flush=True)
    # Build matrix: for each SNP pick allele A (first allele seen in GBR), count copies in the sample.
    P, G = [], []
    for rs in pick:
        rec = have.get(rs)
        if not rec or not all(p in rec["fr"] for p in POPS):
            continue
        alleles = set().union(*[set(rec["fr"][p]) for p in POPS])
        if len(alleles) != 2 or frozenset(alleles) in PAL:
            continue
        a = sorted(alleles)[0]
        g = geno[rs]
        if not set(g) <= alleles:
            continue
        P.append([min(max(rec["fr"][p].get(a, 0.0), 0.005), 0.995) for p in POPS])
        G.append(g.count(a))
    P, G = np.array(P), np.array(G)
    ll = (G[:, None] * np.log(P) + (2 - G)[:, None] * np.log(1 - P)).sum(0)
    rank = sorted(zip(POPS, ll), key=lambda x: -x[1])
    # Supervised admixture EM over MIX pops.
    idx = [POPS.index(p) for p in MIX]
    Q = np.full(len(idx), 1 / len(idx)); Pm = P[:, idx]
    for _ in range(500):
        pm = Pm @ Q
        wa = G[:, None] * (Pm * Q) / pm[:, None]
        wb = (2 - G)[:, None] * ((1 - Pm) * Q) / (1 - pm)[:, None]
        Qn = (wa + wb).sum(0); Qn /= Qn.sum()
        if np.abs(Qn - Q).max() < 1e-7:
            Q = Qn; break
        Q = Qn
    # Bootstrap for confidence.
    rng = np.random.default_rng(1030); boots = []
    for _ in range(100):
        s = rng.integers(0, len(G), len(G)); Gb, Pb = G[s], Pm[s]; Qb = Q.copy()
        for _ in range(200):
            pm = Pb @ Qb
            Qb = (Gb[:, None] * (Pb * Qb) / pm[:, None] + (2 - Gb)[:, None] * ((1 - Pb) * Qb) / (1 - pm)[:, None]).sum(0); Qb /= Qb.sum()
        boots.append(Qb)
    lo, hi = np.percentile(boots, [5, 95], axis=0)
    res = {"snps_used": int(len(G)), "rank": [[p, round(float(v - rank[0][1]), 1)] for p, v in rank],
           "admix": {p: {"est": round(float(q), 3), "lo90": round(float(l), 3), "hi90": round(float(h), 3)} for p, q, l, h in zip(MIX, Q, lo, hi)}}
    (out / "ancestry.json").write_text(json.dumps(res, indent=1))
    print("SNPs used", res["snps_used"]); print("rank (log-lik vs best):", res["rank"][:8]); print("admix:", res["admix"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
