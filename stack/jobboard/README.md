# Job board

A small local page that shows the GPU transcription queues and lets you pause, resume, start or stop them.
Python 3.11+ standard library only; nothing to pip install. See `stack/requirements/jobboard.txt` for the optional tools (pandoc, ssh, ffprobe).

```
cp config/jobboard.example.toml config/jobboard.toml   # then fill in your paths (this file is git-ignored)
python3 stack/jobboard/jobboard.py --dry-run           # try it: buttons only report what they would do
python3 stack/jobboard/jobboard.py                     # live
# open http://127.0.0.1:8797/
```

## What it shows
- **GPU host:** memory used, utilization, number of workers running, and whether the pause flag is set (read over ssh, cached 15 s).
- **Queues:** done / total for every queue file, worked out from which result files exist.
- **Runners:** the queue-runner processes on this computer and the queue each one is reading.
- **Recent log lines:** only status lines (`time label: ok | FAIL | SKIP_LONG`, `STAGE …`, `…_DONE`). Lines with paths or file names are never shown.

## Automatic staging cleanup
With `auto_clear_stale = true`, the board removes the GPU host's **staging copies** (`<label>.orig48k.wav`, `<label>.lev.wav`) of items that
already finished, or that have sat longer than `stale_after_s` (default 8 h) with **no worker process using them**. It checks the running
workers' `--label` first. Originals are never touched. In dry-run it only reports what it would clear.

## Also on the page
- GPU host CPU, memory, GPU memory/busy/temperature, and this computer's load.
- Items on the GPU now, with an estimated progress bar (from the median speed of recent items).
- Recently finished items with finish times; each queue's created time, and optional purpose / source / expected gain / outputs
  from `registry_file`; links to local report files listed in `reports`.

## Controls
| Button | What it does |
|---|---|
| Pause | creates the pause flag on the GPU host. Runners finish the item they are on and start nothing new. |
| Resume | removes the pause flag. |
| Start | starts the runner for one queue in the background, logging to `log_dir`. Refused if that queue already has a runner, or if it is waiting in a running chain script (`chained_queues`). |
| Stop | stops one runner process (only processes matching `runner_match`). The item already on the GPU finishes. |

## Safety
- Listens on **127.0.0.1 only**. Not reachable from the network.
- Every control call needs the per-run token embedded in the page (a new one each start), and a localhost `Host` header. Other websites can't trigger it.
- Only queue names, counts and item labels appear on the page; no source file names, no transcript text.
- `--dry-run` (or `dry_run = true`) makes every button report its command instead of running it.

## Redacted mode (for demos)
`python3 stack/jobboard/jobboard.py --redact` (or `redact = true`) blocks out every term listed in `redact_file`
(one per line, git-ignored; prefix `cs:` for case-sensitive short terms) plus phone numbers, emails, street addresses,
SSNs and long digit runs, in the status data and in every report page. Only the visible text is changed, so the page keeps working.
