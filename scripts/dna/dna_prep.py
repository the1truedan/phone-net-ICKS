#!/usr/bin/env python3
"""Turn a raw genotype file (23andMe format) into inputs for yhaplo and haplogrep3.

  python3 -I dna_prep.py raw.txt out_dir rcrs.fasta

Writes:
  sample_Y.genos.txt  sample-major text for yhaplo (row 0 = GRCh37 positions)
  sample_MT.vcf       chip VCF for haplogrep3 (REF from the rCRS fasta that ships with
                      haplogrep3 trees; use `haplogrep3 classify --chip`)
"""
import sys
from pathlib import Path


def main(raw, out, rcrs):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    ref = "".join(l.strip() for l in open(rcrs) if not l.startswith(">"))
    ypos, yg, mt = [], [], []
    for line in open(raw):
        f = line.rstrip("\n").split("\t")
        if len(f) < 4 or not f[2].isdigit():
            continue
        a = f[3][0] if f[3] and f[3][0] in "ACGT" else None
        if f[1] == "Y":
            ypos.append(f[2]); yg.append(a or ".")
        elif f[1] in ("MT", "M") and a:
            p = int(f[2]); r = ref[p - 1]
            mt.append((p, f"MT\t{p}\t{f[0]}\t{r}\t{'.' if a == r else a}\t.\tPASS\t.\tGT\t{0 if a == r else 1}"))
    (out / "sample_Y.genos.txt").write_text("ID\t" + "\t".join(ypos) + "\nsample\t" + "\t".join(yg) + "\n")
    hdr = "##fileformat=VCFv4.2\n##contig=<ID=MT,length=16569>\n##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample\n"
    (out / "sample_MT.vcf").write_text(hdr + "\n".join(r for _, r in sorted(mt)) + "\n")
    print(f"Y sites {len(ypos)}, MT sites {len(mt)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
