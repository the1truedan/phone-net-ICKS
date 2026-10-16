#!/bin/bash
# 2026-10-15: Tower CPU lane. Best-quality CPU transcript on Tower's idle Xeon threads, throttled (nice 19, ionice -c3, 16 of 36 threads).
# Usage: tower_cpu_transcribe.sh <audio> <out_prefix_local> [initial prompt]
# Audio is cleaned to 16 kHz mono on this Mac (Tower has no ffmpeg), shipped, transcribed, pulled back, and the remote copies deleted.
set -e
HOST=${TOWER_HOST:-tower}; L=${TOWER_LANE_DIR:-/mnt/ai-data/work/tower_cpu_lane}; CUSTODY=${CUSTODY_LOG:-}; SRC="$1"; OUT="$2"; PROMPT="${3:-}"
id=$(shasum -a 256 "$SRC" | cut -c1-12); tmp=$(mktemp -d)
ffmpeg -nostdin -v error -y -i "$SRC" -af "highpass=f=70,lowpass=f=8000,afftdn=nf=-25,loudnorm=I=-18:TP=-2:LRA=11" -ar 16000 -ac 1 "$tmp/$id.wav"
scp -q "$tmp/$id.wav" $HOST:$L/in/
ssh -o BatchMode=yes $HOST "cd $L && LOWPRIO_THREADS=${TOWER_THREADS:-16} OMP_NUM_THREADS=${TOWER_THREADS:-16} nice -n 19 ionice -c3 $L/venv/bin/python $L/tower_fw.py in/$id.wav out/$id $(printf %q "$PROMPT")"
scp -q $HOST:$L/out/$id.json "$OUT.json"; scp -q $HOST:$L/out/$id.md "$OUT.md"
ssh -o BatchMode=yes $HOST "rm -f $L/in/$id.wav $L/out/$id.json $L/out/$id.md"
rm -rf "$tmp"
[ -n "$CUSTODY" ] && $CUSTODY derive "$OUT.md" from=$id lane=tower_cpu model=faster-whisper-large-v3-int8 >/dev/null 2>&1 || true
