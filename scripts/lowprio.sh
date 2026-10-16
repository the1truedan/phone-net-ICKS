#!/bin/bash
# 2026-10-15: run a CPU-heavy job so it yields to everything else on the box.
# macOS: background QoS (taskpolicy -b → efficiency cores, low I/O) + nice 15.  Linux (Tower/MRGPU): nice 19 + idle I/O class.
# Also caps math-library threads to LOWPRIO_THREADS (default: half the cores) so one job can't take the whole machine.
n=$( (sysctl -n hw.ncpu 2>/dev/null || nproc) ); T=${LOWPRIO_THREADS:-$(( n / 2 ))}
export OMP_NUM_THREADS=$T MKL_NUM_THREADS=$T OPENBLAS_NUM_THREADS=$T CT2_INTER_THREADS=1 LOWPRIO_THREADS=$T
if [ "$(uname)" = Darwin ]; then exec taskpolicy -b nice -n 15 "$@"; else exec nice -n 19 ionice -c3 "$@"; fi
