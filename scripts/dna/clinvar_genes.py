#!/usr/bin/env python3
"""Fetch PUBLIC ClinVar data for a gene list (no personal data is sent), save locally.

  python3 -I clinvar_genes.py out_dir

Per gene: GRCh37 gene span (NCBI Gene) and every ClinVar variant classified
pathogenic / likely pathogenic, with its dbSNP rsID and GRCh37 position when present.
Writes clinvar_plp.jsonl and gene_spans.json. Only gene names go to NCBI.
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

GENES = ["COL3A1", "COL5A1", "COL5A2", "COL1A1", "COL1A2", "TNXB", "FBN1", "TGFBR1", "TGFBR2", "SMAD3",
         "TGFB2", "TGFB3", "ACTA2", "MYH11", "MYLK", "PRKG1", "LOX", "PKD1", "PKD2", "PLOD1",
         "ADAMTS2", "C1R", "C1S", "ZNF469", "FKBP14", "CHST14", "B4GALT7", "SLC2A10"]
E = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def get(path, **q):
    q.setdefault("retmode", "json")
    url = E + path + "?" + urllib.parse.urlencode(q)
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                time.sleep(0.4)
                return json.load(r)
        except Exception:
            time.sleep(2 + 2 * i)
    raise SystemExit(f"failed: {url[:120]}")


ACMG = "ACTA2 ACTC1 ACVRL1 APC APOB ATP7B BAG3 BMPR1A BRCA1 BRCA2 BTD CACNA1S CALM1 CALM2 CALM3 CASQ2 COL3A1 DES DSC2 DSG2 DSP ENG FBN1 FLNC GAA GLA HFE HNF1A KCNH2 KCNQ1 LDLR LMNA MAX MEN1 MLH1 MSH2 MSH6 MUTYH MYBPC3 MYH11 MYH7 MYL2 MYL3 NF2 OTC PALB2 PCSK9 PKP2 PMS2 PRKAG2 PTEN RB1 RBM20 RET RPE65 RYR1 RYR2 SCN5A SDHAF2 SDHB SDHC SDHD SMAD3 SMAD4 STK11 TGFBR1 TGFBR2 TMEM127 TMEM43 TNNC1 TNNI3 TNNT2 TP53 TPM1 TRDN TSC1 TSC2 TTN TTR VHL WT1 F5 F2 CHEK2 ATM".split()


def main(out, which="panel"):
    global GENES
    if which == "acmg":
        GENES = [g for g in ACMG if g not in GENES]
    out = Path(out)
    spans, n = {}, 0
    with open(out / "clinvar_plp.jsonl", "w") as fh:
        for g in GENES:
            gid = get("esearch.fcgi", db="gene", term=f"{g}[sym] AND human[orgn]")["esearchresult"]["idlist"][:1]
            if gid:
                s = get("esummary.fcgi", db="gene", id=gid[0])["result"][gid[0]]
                for h in s.get("locationhist", []):
                    if h.get("assemblyaccver", "").startswith("GCF_000001405.25"):
                        spans[g] = {"chr": h["chraccver"], "start": min(h["chrstart"], h["chrstop"]) + 1, "stop": max(h["chrstart"], h["chrstop"]) + 1}
                        break
            term = f'{g}[gene] AND ("clinsig pathogenic"[Properties] OR "clinsig likely pathogenic"[Properties])'
            ids = get("esearch.fcgi", db="clinvar", term=term, retmax=10000)["esearchresult"]["idlist"]
            for i in range(0, len(ids), 200):
                res = get("esummary.fcgi", db="clinvar", id=",".join(ids[i:i + 200]))["result"]
                for vid in res.get("uids", []):
                    v = res[vid]
                    rs, pos37 = None, None
                    for vs in v.get("variation_set", []):
                        for x in vs.get("variation_xrefs", []):
                            if x.get("db_source") == "dbSNP":
                                rs = "rs" + x["db_id"]
                        for loc in vs.get("variation_loc", []):
                            if loc.get("assembly_name") == "GRCh37" and loc.get("status") == "previous":
                                pos37 = (loc.get("chr"), loc.get("start"))
                    cls = (v.get("germline_classification") or {}).get("description") or (v.get("clinical_significance") or {}).get("description")
                    traits = [t.get("trait_name") for t in (v.get("germline_classification") or {}).get("trait_set", [])][:3]
                    fh.write(json.dumps({"gene": g, "id": vid, "title": v.get("title"), "rs": rs, "pos37": pos37, "class": cls, "traits": traits}) + "\n")
                    n += 1
            print(g, len(ids), flush=True)
    (out / "gene_spans.json").write_text(json.dumps(spans, indent=1))
    print("total", n, "spans", len(spans))


if __name__ == "__main__":
    main(*sys.argv[1:3])
