# Which machine runs what, and how to keep each one usable (2026-10-15)

From past runs (Sept 24 – Oct 15, 2026) and the job board. No PII.

## The three machines

| Machine | Strong at | Weak at | Runs these jobs |
|---|---|---|---|
| **MRGPU** (Linux, RTX 4060 Ti 16 GB) | CUDA: WhisperX large-v3, diarization, voiceprints | 16 GB VRAM is shared by everything on it | **Deep passes** (one at a time), the resident fine-comb worker, local LLM scoring *only when no deep pass runs* |
| **M4RV** (this Mac, M-series, 10 cores) | Fast single cores; Apple GPU (Metal); phone USB; the 2 TB custody disk | It is also the desk you work at; no CUDA | **Phone pulls** (adb), custody log, job board, **quick triage** (whisper.cpp on the Apple GPU), cutting pieces, one-off best-quality CPU transcripts, LLM scoring when MRGPU's GPU is busy |
| **Tower** (Unraid, Xeon E5-2699 v3, 18 cores / 36 threads, no GPU) | Many slow cores; local disk with no network hop for `/mnt/ai-data` | Shares 32 GB RAM with fast-models, bees and the docker stack; no GPU | File walks, hashing, dedup, named-subpath rsync, AgentsView, Headroom/LiteLLM. **CPU lane (live 2026-10-15):** faster-whisper large-v3 int8 in `/mnt/ai-data/work/tower_cpu_lane` (venv + model), always throttled |

## Rules that came from real failures

1. **One GPU job per GPU.** An Ollama model left loaded (6.5 GB) next to the deep pass caused CUDA out-of-memory on 7 of 11 recordings (Oct 15). Unload with `keep_alive: 0`. Don't start the resident worker beside per-file jobs (Oct 2).
2. **Gate every GPU item on free VRAM, and honor a pause file.** Then renders and other jobs never starve.
3. **Move LLM scoring off a busy GPU.** When MRGPU runs a deep pass, score on the M4RV Ollama.
4. **Keep the data where it lives.** The custody disk is on M4RV, and all three machines share Tower's single 1 GbE NIC. Ship small audio files, not whole folders.
5. **Long files go last.** "Defer to end" beats killing a job.
6. **Never append ad-hoc lines to a batch job's log.** The board reads new lines as progress.
7. **Background priority can starve an urgent job.** `taskpolicy -b` held an urgent transcript at 0% CPU (Oct 16). Run urgent work at normal priority, or lift it with `taskpolicy -B -p <pid>`, and set `HF_HUB_OFFLINE=1` so the model library does not wait on the network.

## Throttling, so that one job never kills the others

Use `scripts/lowprio.sh <command>` for any CPU-heavy job.
- **macOS:** `taskpolicy -b` (background QoS: efficiency cores, low I/O priority) plus `nice 15`. Foreground apps stay responsive.
- **Linux (Tower, MRGPU):** `nice 19` plus `ionice -c3` (idle I/O).
- **Thread cap:** `LOWPRIO_THREADS` (default: half the cores) is passed to OpenMP/MKL/OpenBLAS. For faster-whisper, also set `cpu_threads` to the same number.
- **Deep pass on MRGPU:** its CPU side (audio leveling, alignment) runs under `nice 10, ionice -c3`.
- On Tower, keep at least 8 threads and 8 GB RAM free for Unraid, docker and bees.

## Routing, job by job

| Job | Where | Why |
|---|---|---|
| Phone pull, custody, board | M4RV | USB + custody disk |
| Quick triage (small.en) | M4RV Apple GPU, `lowprio` | Fast; leaves the CPU free |
| Deep pass (diarized, beam 10) | MRGPU, queued one at a time | Needs CUDA |
| One urgent best-quality transcript | M4RV CPU (`lowprio`, 5 threads) or MRGPU if idle | Fast cores; no copying |
| Many CPU transcripts at once | **Tower CPU lane** (nice 19, ionice -c3, 16 threads; tested 2026-10-15: 18 s audio in 11 s incl. model load) | 36 threads sit idle; remote copies deleted after pull-back |
| LLM scoring (qwen3.5:9b) | MRGPU if its GPU is idle; else M4RV | One GPU job per GPU |
| Embedding (bge-m3) | M4RV Ollama | Index lives here |
| Hashing, dedup, walks on ai-data | Tower, `nice 19 ionice -c3` | No network hop |
