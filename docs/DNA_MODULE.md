# DNA module (v0.7.9)

A family can have a raw DNA file on a shelf for years. This module reads one on the home computer and turns it into
plain-language pages for the family. **No genotype ever leaves the computer.** The only things sent to public databases
are gene names and marker IDs (rsIDs), never the person's letters at those markers.

## What it reads

A raw genotype file in **23andMe text format** (`rsid  chromosome  position  genotype`, GRCh37). Research studies
(for example Genes for Good) and most consumer tests can export this format.

## Breakthrough (2026-10-30): a 9-year-old file, read in one evening

- The file was made in **August 2017** and was copied into a notes vault in **June 2026**. Chat assistants had only seen a
  pasted list of 45 markers. Nobody had read the whole file: **9 years, 63 days** on the shelf.
- In one evening, on local hardware: **563,289 markers** (100% called), **731 Y-chromosome** and **310 mitochondrial** markers.
- **Father's line** (Y haplogroup) with 23andMe's open-source **yhaplo**, and **mother's line** (mtDNA haplogroup) with
  **haplogrep3** (University of Innsbruck), both run offline.
- **Quality checks** (standard library only): call rate, sex check from X and Y, runs of homozygosity.
- **Known-variant check:** public ClinVar "pathogenic / likely pathogenic" lists for a gene panel the family chooses,
  and for the ACMG list of medically actionable genes, matched against the file **on the home computer**. Strict rule: same
  rsID **and** the person carries the changed letter. A first, loose pass (position only) gave false alarms: a common,
  harmless variant sits at the same spot as a rare frameshift. The strict rule removes that class of error.
- **Ancestry check:** 1000 Genomes allele frequencies for 26 populations (Ensembl, IDs only), scored on the home computer
  with a likelihood ranking and a simple admixture fit with bootstrap ranges.
- **Paper trail beside the DNA:** family-tree exports (GEDCOM) from three genealogy programs, cross-checked slot by slot,
  with one primary record (a birth certificate) as the tie-breaker.
- Results went into **private, large-type PDFs for the family**, with charts. They are not in this repository.

## Timeline of one run

| Step | Time |
| --- | --- |
| Find the file (local session index + vault search) | minutes |
| Install tools (`pip install` yhaplo from GitHub, numpy, pandas, matplotlib; haplogrep3 release tarball + Java 17) | ~2 min |
| Y and mtDNA haplogroups | seconds |
| ClinVar download (public, per gene) | ~10 to 40 min (NCBI rate limits) |
| 1000 Genomes frequencies (Ensembl REST, 3,000 IDs) | ~1 h (network bound, not CPU bound) |
| Charts and PDF | minutes |

## Install

```sh
python3 -m venv dna-venv
dna-venv/bin/pip install "git+https://github.com/23andMe/yhaplo.git@2.1.17" numpy pandas matplotlib
mkdir hg3 && curl -L -o hg3/hg3.tar.gz https://github.com/genepi/haplogrep3/releases/download/v3.3.2/haplogrep3-3.3.2-linux.tar.gz
tar -xzf hg3/hg3.tar.gz -C hg3        # the Linux build runs on macOS with Java 17
(cd hg3 && ./haplogrep3 install-tree phylotree-fu-rcrs@1.3)
```

## Run

```sh
python3 -I scripts/dna/dna_basic.py raw.txt out/                     # quality checks
python3 -I scripts/dna/dna_prep.py raw.txt out/ hg3/trees/phylotree-rcrs/17.3/rcrs.fasta
dna-venv/bin/yhaplo -i out/sample_Y.genos.txt -o out/yhaplo -aao      # father's line
(cd hg3 && ./haplogrep3 classify --tree phylotree-fu-rcrs@1.3 --in ../out/sample_MT.vcf \
   --out ../out/mt.txt --chip --extend-report --hits 5)               # mother's line
python3 -I scripts/dna/clinvar_genes.py out/panel                      # public ClinVar, gene names only
python3 -I scripts/dna/clinvar_genes.py out/acmg acmg
dna-venv/bin/python -I scripts/dna/ancestry_1kg.py raw.txt out/ancestry 3000
```

## Limits (say them out loud)

- **Chip data is not sequencing.** Chips miss most rare variants, and published work shows that rare "pathogenic" calls
  from consumer chips are often false. Any medical finding must be confirmed by a clinical lab. A clean chip does **not**
  rule a condition out.
- Haplogroups go only as deep as the chip goes. A Y-DNA sequencing test is needed for surname-project matches.
- 1000 Genomes has no Irish or German panel. "English vs German vs Irish" cannot be split with this reference.
- Health results are for a genetic counselor to read with the family, not for this page.
- Faster ancestry: download the 1000 Genomes genotypes once to the storage server and score locally (PCA, admixture)
  instead of waiting on a public web service.
