#!/usr/bin/env bash
# THE PAPE: scan the ScanSnap S1500/S1500M feeder (both sides) -> searchable PDF, all local (SANE + ocrmypdf/Tesseract).
# Same custody files as a phone pull: SHA256SUMS.txt + custody_log.txt + PULL_LOG.txt ("pages k" lines).
#   bash scripts/pape_scan.sh [out_dir] [name]      # default out: ${PAPE_OUT:-~/pape_scans}/<date>
set -uo pipefail
O=${1:-${PAPE_OUT:-$HOME/pape_scans}/$(date +%F)}; NAME=${2:-scan_$(date +%H%M%S)}
DEV=$(scanimage -L 2>/dev/null | sed -n "s/^device \`\(fujitsu:[^']*\)'.*/\1/p" | head -1)
[ -n "$DEV" ] || { echo "No ScanSnap found: open the chute, USB direct to the Mac"; exit 1; }
mkdir -p "$O/$NAME.pages"; LOG=$O/PULL_LOG.txt; ts(){ date '+%F %T'; }
echo "$(ts) phase1 start paper scan $DEV -> $O/$NAME.pdf" >> "$LOG"
T0=$(date +%s)
# both sides, color 300 dpi, auto page length, deskew + crop in the scanner driver, skip blank backs (<1% ink)
scanimage -d "$DEV" --source 'ADF Duplex' --mode Color --resolution 300 --ald=yes --swdeskew=yes --swcrop=yes --swskip 1 \
  --format=tiff --batch="$O/$NAME.pages/p%04d.tif" 2>&1 | grep -E 'Scanned page|out of documents|error' \
  | while read -r l; do echo "$(ts) $l" >> "$LOG"; done
# blank backs the scanner's --swskip misses: <0.2% dark pixels -> moved to blank/ (kept, not OCR'd)
python3 - "$O/$NAME.pages" <<'EOF'
import sys, glob, os
from PIL import Image
d = sys.argv[1]; os.makedirs(d + "/blank", exist_ok=True)
for f in sorted(glob.glob(d + "/*.tif")):
    g = Image.open(f).convert("L").reduce(4)
    if sum(g.histogram()[:128]) / (g.width * g.height) < 0.002:
        os.rename(f, f"{d}/blank/{os.path.basename(f)}")
EOF
B=$(ls "$O/$NAME.pages/blank"/*.tif 2>/dev/null | wc -l | tr -d ' '); echo "$(ts) blank sides set aside $B" >> "$LOG"
N=$(ls "$O/$NAME.pages"/*.tif 2>/dev/null | wc -l | tr -d ' ')
[ "$N" -gt 0 ] || { echo "$(ts) STOP: 0 pages (feeder empty?)" >> "$LOG"; echo "0 pages: put paper face-down, top edge first"; exit 2; }
echo "$(ts) pages scanned $N" >> "$LOG"
img2pdf "$O/$NAME.pages"/*.tif -o "$O/$NAME.raw.pdf"
ocrmypdf -q --rotate-pages --rotate-pages-threshold 1 --deskew --clean --optimize 2 --jobs 8 -l eng "$O/$NAME.raw.pdf" "$O/$NAME.pdf" \
  && rm -f "$O/$NAME.raw.pdf"
W=$(pdftotext "$O/$NAME.pdf" - 2>/dev/null | wc -w | tr -d ' ')
(cd "$O" && find . -type f ! -name 'SHA256SUMS.txt' ! -name 'PULL_LOG.txt' ! -name 'custody_log.txt' -print0 | xargs -0 shasum -a 256 > SHA256SUMS.txt)
S=$(( $(date +%s) - T0 ))
echo "$(date '+%F %T %Z') $DEV paper scan $NAME: $N page images, OCR $W words, ${S}s; originals kept as TIFF; sha256 in SHA256SUMS.txt" >> "$O/custody_log.txt"
echo "$(ts) phase1 done · SAFE TO UNPLUG: $N pages, $W words, ${S}s" >> "$LOG"
echo "$O/$NAME.pdf  ·  $N pages · $W words · ${S}s"
