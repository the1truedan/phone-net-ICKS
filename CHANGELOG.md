# Changelog

## v0.7.8 — 2026-10-27 · na^3 boo x2 edition (work from 2026-10-23 to 2026-10-26; temp name "Gonna Need a Bigger Book")
- **Breakthrough (Dan, 2026-10-23):** a model's "red flag" only counts when it cites its evidence. "Contradicts self" must name the
  other statement; "conflicts with the record" must name a numbered record line. A script checks every cite. The first 9B pass
  labelled 49 of 74 high flags "contradicts self" from one statement alone; the cite rule removes that class of error for any model.
- **Bake-off:** the same meeting statements rated by 5 local models (9B to 27B) on one GPU, one model at a time, with memory
  guards (unload before load, free-VRAM check, fixed context, timeouts). Pick by measured agreement, not model size.
- **Job board:** `problem_lists` config (unreadable, encrypted or private files count as "problem", not "left" or "uncovered";
  Start/Priority no longer re-run a skip forever). New recon job names for camera-audio sync, clip transcripts, fusion, position.
- **Ops:** GPU host Ollama container now one model / one request, flash attention, q8 KV cache; storage host Ollama capped at 10 GB.
- **Send night (2026-10-26), a hard week of round-the-clock care:** one late reply checked against the written list of meeting
  promises: 1 of 10 items arrived (an undated guideline sheet). The follow-up quotes that sheet's own tests back as numbered
  questions instead of opinion. Sent: 2 secure-portal messages (one to 12 people, one records request with 10 numbered items) and
  3 plain emails (escalation, grievance, ombudsman), all with a confirm-receipt request and one answer date.
- **Breakthrough: one address, three microphones.** An email address spelled aloud at a meeting was searched for on every device
  that recorded that day. 1 of 3 sources caught the letters (the other two were off or caught only "email is"). The spelling and the
  one source are written down, and the reply asks the speaker to forward the request if the address is wrong.
- **Breakthrough: the portal that cannot forward.** The agency's secure portal would not add outside recipients to a reply or
  forward a sent message. Work-around: export the sent text, then paste it into a plain email that uses initials only. The note to
  the agency names this as a reason to also answer by letter or regular email.
- **Tone, measured:** the caregiver's raw reactions stay in local notes. The letters carry dates, counts and the agency's own words.
  One letter thanks staff for an answer they gave on time and apologises for short replies sent earlier. 9 old drafts were backed up
  and then deleted so that old text could not be sent by mistake. A large-print, one-page send sheet was printed, and the message
  text was put on the clipboard so it could be pasted, not retyped.
- **Old budget sheet vs new (2026-10-26):** an older budget sheet found in an old desktop folder was read on the home computer
  only and set beside the newer sheets. The newest written number matches the payroll certification, not the number said by
  phone, and the number said at the meeting is not in writing yet. Exact hours and ratings stay in the private record.
- **Why the numbers are what they are:** the agency's own cue sheet holds the levers: every need must also be on the functional
  screen; family caregivers are not paid for chores that also help others in the house; "multi-tasking" cuts time; many tasks are
  "typically" capped unless a doctor or therapist recommends more; overnight and supervision rows have their own tests. A local
  model (9B, home computer only) now checks each lever against the medical record lines and must cite each line; uncited claims are
  removed by script.
- **Old paper trail into custody:** 53 files from 2025 (payroll exports, letters, two recorded payroll-company calls with
  transcripts) copied into the evidence folder with SHA-256, without moving the originals.
- **Session tips (what worked on a hard night):** ask "are you using this box?" before any load test (a guard now refuses to start
  while a game or Steam runs); keep raw reactions in local notes and put dates and counts in letters; check a late reply against the
  written promise list; when a secure portal cannot forward, export the text and paste it into a plain email with initials only;
  print a large-type send sheet and put the message on the clipboard; run medical comparisons on local models only, and keep the
  GPU box free while it is being measured.
- **Live stats (2026-10-27):** hospice start date (Oct 14); 10.5 h a day said at the Oct 21 meeting, shown as a dotted mark (not in
  writing, not paid); 1 of 10 promised items arrived; follow-up counts (2 portal messages, 41 numbered questions, 10-item records
  request, 3 emails, 0 replies yet); portal lockouts. The notes chart explains that fewer notes now means comfort care, kept private.
- **Compute, measured (2026-10-27):** new chart of home GPU load per day from the GPU's own metrics (Aug 28 to Oct 26). Oct 23–25
  (meeting recordings and statements checked): 38.8 busy hours in 3 days, about 9× the Oct 4–22 daily average. Correspondence scope:
  22 / 25 email threads with the care agency / payroll company; 8 / 2 secure-portal messages received. Generic names only.
- **Privacy:** counts only. No names, no medical detail, no quotes.

## v0.7.7 — 2026-10-19 · Disclosure Edition
- **Code name:** Disclosure Edition. In this release, the family asked all parties for one meeting with full disclosure, both ways.
- **Live page numbers (2026-10-19):** 2,624 recordings catalogued; 28 device pulls; 20 faxes delivered since Sep 1 (3 failed at the
  receiving machine, and an email copy went instead); 41 letters and email drafts checked before sending since Oct 14 (facts, dates,
  tone, legal wording), with 23 saved revisions; 1 all-caps subject line changed to "Please reply by…"; one meeting request to 4 parties,
  with 4 fixed times checked against the advocate's availability.
- **Four new breakthroughs (ASD-STE100 text):** a misheard word settled by two decodes of the same audio; phone answers set beside the
  written questions; private-care windows that the camera tools must skip; visit recordings found by matching the calendar to the
  recordings catalog.
- **Privacy:** counts only. No names, no medical detail, no message text.
- **README:** new "Latest · Disclosure Edition" section (fax and draft-check counts, cited to the live page's totals chart);
  release badge now v0.7.7. **Live page:** footer and job-board eyebrow versions corrected (they still said v0.6.0).

## v0.7.6 — 2026-10-18 · Sessions of Therapy: the AI-use cube
- **New page `sessions.html`:** "Sessions of Therapy" (a play on therapy sessions). 1,649 AI sessions from one caregiver as dots in
  a turning black cube, grouped into 14 topics. A search box and topic chips zoom in; a side panel shows the count, month range,
  messages, output tokens, which tool, and the latest sessions. Sparks show the same week jumping between topics.
- **Also on the page:** where topics overlap, the call-outs and CVE-FAUX wall (AI mistakes caught by the caregiver, including 18
  answers stopped mid-way and 127 mid-turn corrections), the missing-answers count, tool and MCP calls, tokens at API list price
  (not billed), the agents' workbench (commands, folders, files) and the public repos with the goal behind them.
- **Privacy:** metadata only (`sessions_data.js`). No message text, no names, no session IDs (replaced by numbers), dates rounded
  to the month, no paths or hostnames. Topics come from a first keyword pass; a local model will replace it.
- **Links:** the summary chips, workflow footer and README point to the new page.

## v0.7.5 — 2026-10-16 · long job lines stay inside the board
- **Job board:** a long status line (for example a paused multi-day upload with its full transfer stats) no longer pushes the
  CPU/memory/GPU/network bars past the table edge. Status pills wrap in their column (full text on hover), the usage bars shrink to
  fit with each value kept on one line, and long command paths in "Compute users" wrap. No sideways scrolling on the main page.

## v0.7.4 — 2026-10-16 · see the bottleneck: per-job CPU, memory, GPU and network on the board
- **Job board:** every running job (recon jobs, queue runners, Mac cutting/upload jobs, items on the GPU host) shows small bars for
  **CPU** (the job's process and all its children, plus the whole host), **memory** (job RSS or GPU VRAM, plus host free %), **GPU**
  (host utilisation; macOS has no per-process GPU % without sudo) and **network** (per process on the Mac via `nettop`, no sudo;
  whole NIC on the GPU host from `/proc/net/dev`). A **"likely limit"** tag names the bottleneck: GPU ≥ 85%, CPU, memory < 15% free,
  network ≥ 70% of 1 GbE (`nic_mbs` in the config), or "waiting" (disk, remote host or between items).
- **Live page:** three new breakthroughs (10/15 care-record export read locally; 10/16 one visit mapped + "what was said" in one place;
  10/16 per-job bottlenecks, and a side matter dated and handed to counsel); ~90 new recordings from the Oct 14–16 pulls; 18 device pulls.

## v0.7.3 — 2026-10-16 · token tile split into input, output and cache
- **Live page:** the AI-token tile now shows fresh input (109 M) and model output (27 M) first; the 12.55 B total is labeled as mostly
  (98%) cache re-reads of the same context (codeburn breakdown).

## v0.7.2 — 2026-10-16 · a data key for every chart
- **Live page:** new "Data key" section that names the source type behind every chart and number (task-app export, payroll Shift
  Status exports cross-checked with pay stubs, agent session index, recordings catalog, account exports). Source types only; no file
  names or personal detail.
- **May 2025 explained:** the paid line averages 5.99 h/day because one pay period paid 99.25 h (pay stub confirms) instead of the usual
  49 h. It is a real paid amount, not a chart error.

## v0.7.1 — 2026-10-16 · CPU jobs to the many-core server; new numbers; answering a written explanation in 7 days
- **Tower CPU lane:** `scripts/tower_cpu_transcribe.sh` + `scripts/tower_fw.py` send urgent one-off best-quality transcripts
  (faster-whisper large-v3, int8) to the many-core server's idle threads (nice 19, idle I/O, 16 threads), then delete the remote
  copies, so the GPU queue keeps moving. Host, folder and custody-log hook come from environment variables.
- **Job board (from v0.7.0):** progress bars, CPU vs GPU, ETA per job, and the active-process monitor with close/stop buttons to head
  off out-of-memory errors.
- **Live page numbers (2026-10-16):** ~19,100 caregiving notes; 2,461 recordings catalogued (~750 h) + ~80 new; 4,975
  speaker-separated outputs; 60 deep-quality redos; 16 device pulls; ~81 h active AI-assisted admin time since Sep 1 (38 h in the
  Sep 25–29 sprint); 12.55 B AI tokens across Claude, Grok and Codex; 316 care-record documents parsed locally.
- **Live page sections:** "Why the thinking is outsourced" (the caregiver's real situation, no personal detail); "Answering a
  written explanation, fast" (counts and method only); "Time to process" now shows the staged deep queue (1,664 recordings, ~350 h
  audio, ~320 GPU hours).

## v0.7.0 — 2026-10-16 · job board shows progress, ETA and value per job; host routing and throttling
- **Job board, "Other recon jobs":** jobs started outside the board now show a progress bar, CPU vs GPU, elapsed time, and an **ETA
  learned from past runs** (audio length from a catalog × the measured speed of finished items in the same queue, or a small history
  file). Each row has a **"what this gains" drop-down**. Quick passes show a tally (done / queued per run). Same-recording results and
  empty files count as done; open-ended jobs show paused or idle.
- **No case data in the code:** job names, "gains" text and queue paths now come from a `[recon_jobs]` table in the git-ignored board
  config. `config/jobboard.example.toml` shows a generic example.
- **New doc:** `docs/HOST_ROUTING_AND_THROTTLE.md`, which machine runs what (GPU box, desk Mac, many-core server), and 7 rules learned
  from real failures (one GPU job per GPU, gate on free VRAM, long files last, background priority can starve an urgent job).
- **New tool:** `scripts/lowprio.sh <command>`, which runs a CPU-heavy job so it yields: macOS background QoS + nice 15; Linux nice 19 +
  idle I/O; math-library threads capped at half the cores.
- Numbers on the live page are unchanged from v0.6.0 (2026-10-12).

## v0.6.0 — 2026-10-12 · out-of-date lights, camera-clip saving with a person in the loop, old-phone backup recovery
- **Breakthroughs (2 new, 15 total):** camera clips saved from the phone app over USB with a person in the loop (only Download,
  Share or "Not now" are ever tapped; every clip's file time is checked against its target minute; expiring clips first; the to-do
  pages are stamped after each run), and a 2020 LG Bridge full-phone backup (`.lbf`) read without the vendor app.
- **New tool:** `scripts/lbf_extract.py` streams the ZIP entries inside an `.lbf` (the small index is scrambled, the entries are not),
  writes a SHA-256 manifest of every entry and extracts databases and recordings. Read-only on the backup.
- **Job board:** an out-of-date light on every report page and in the report list (green / yellow / red / grey) from the newest
  data each report depends on (`freshness_sources`, per-report `sources`, `freshness_red_h`); hours and minutes; live reload of queue
  and batch lists; open-ended batch jobs; a panel for what is using the Mac GPU; generic host keys. Finished voicemail queues keep
  their done rows, so they no longer read 0 of 0.
- **Camera-clip queues:** short urgency queues (expiring, daytime, deep early-morning scrolls); each line ends pulled / not in the app
  list / past the scroll limit / queued; indoor cameras that cannot see the street are flagged.
- **By the numbers (2026-10-12):** 2,436 phone-pull recordings checked by hash (2,430 covered); 4,715 speaker-separated outputs
  (incl. 1,089 chunks); 296 named-caller voicemails QC'd with speaker-name confidence; 325 camera clips pulled and timestamp-checked;
  568 ledger days.
- **Live page:** new "Job board, in the open" and "Getting a packet to the right desk" sections (generic handoff practice: one
  question per office, exhibits with file, timestamp and SHA-256, a person listens before anything is cited, safety concerns about
  someone else go through a licensed professional). No names, agencies or case details.

## v0.5.11 — 2026-10-03 · the requests behind the two newest breakthroughs
- **Breakthroughs:** the two newest entries now quote the owner's own request from the session index (time-stamped, IDs only), as a historical note
  of how each step started: running jobs concurrently with a small-model first pass, and a watch folder for new phone pulls.
- Final numbers unchanged from v0.5.10: 2,267 of 2,271 recordings fully processed (2 unreadable, 2 not recordings); 3,600 speaker-separated
  recordings and pieces.

## v0.5.10 — 2026-10-03 · new numbers, two new breakthroughs
- **By the numbers:** 2,290 recordings indexed (every phone pull, checked by hash); 3,600 recordings and long-file chunks fully speaker-separated
  (2,283 + 1,317 chunks), every readable recording done; 90 emails indexed; 560 days in the day-by-day ledger.
- **Breakthroughs:** two computers at once (a quick small-model pass on the Mac's GPU beside the CUDA deep pass), and coverage of every phone pull with a
  recovery step for damaged files (header rebuild, damaged-frame salvage, untrunc in a container).
- Includes v0.5.9 (report pages with section cards, contents bar, callouts, aligned numbers and colour chips).

## v0.5.9 — 2026-10-02 · report pages with cards, contents bar and colour
- **Report pages:** each section is a card with a coloured edge; a contents bar links to each section; quotes become callout
  boxes; numbers align right; ✅ and ⚠️ get colour; bold table words listed in `report_chips` become coloured chips
  (for example, the party that a row points to). Long headings no longer break the layout (pandoc `--wrap=none`).

## v0.5.8 — 2026-10-02 · coverage of every phone pull
- **Coverage panel (watch folder):** the job board now reads the checksum list (`SHA256SUMS*.txt`) that every phone pull writes
  (`pull_manifest_globs`) and checks each audio file, by hash, against the catalog, the results and the queues. It scans again
  when a pull is added or a list changes. One row per pull: done, plain transcript only, queued, **not covered**, not in the catalog, ignored.
- **Queue uncovered:** writes the recordings that nothing covers to a new queue (`AV_QUEUE_U<MMDD>.tsv`) with a purpose note.
  Nothing starts until you press Start. **Add to catalog:** appends one row per uncatalogued file (backup first; existing rows unchanged).
- **Why:** before this, the board counted only hand-made queues. A check of all pulls found 97 recordings (about 25 GB, mostly
  from an older SD card) that no queue or result covered, and a catalog that stopped at the 2026-09-29 pulls.

## v0.5.7 — 2026-10-02 · evening numbers, job board counts long recordings correctly
- **By the numbers:** 2,800 recordings and long-file chunks fully speaker-separated (2,031 recordings + 769 chunks), up from 2,568.
  Every long-file piece that was waiting is processed or confirmed silent. The quick first pass ran on 79 pieces.
- **Job board:** a long recording that is processed in 15-minute pieces now counts as done when every piece is processed or
  confirmed silent (`chunk_tier_glob`, `silent_lists`), and chunk manifests count as results (`extra_result_patterns`).
  Before this, such queues showed 0 done although the work was complete. Rows say how many pieces are still queued.

## v0.5.6 — 2026-10-02 · two computers on the job board, quick first pass, saturation watch
- **Active jobs** (was "On the GPU now"): the GPU host's deep pass and the Mac's work in one table, each row with a host badge
  (🍎 Mac, 🐧 Linux GPU host, 🗄 storage server) and a progress bar. Mac progress is real where it can be measured (bytes of a piece
  being cut, lines of a batch script's log) and marked "estimated" otherwise (quick triage, silence check).
- **Per-host CPU, GPU and network**, including the Mac's GPU (read from the graphics driver's statistics, no sudo) and the storage
  server's 1 GbE link, with a plain-language **saturation** line (GPU memory > 90 %, RAM < 10 % free, CPU > 90 %, a link above
  about 95 MB/s, or server load above its thread count).
- **Quick first pass on long recordings** (60 min and up): a small model (whisper.cpp `small.en`) on the Mac's GPU scores each
  15-minute piece; pieces with case terms or real talk go to the deep pass, the rest are listed for later and never dropped.
  On a 16-hour recording, 12 of 65 pieces needed the deep pass.
- **Fixed:** ⇧ Priority could pause a runner's own subshell (its per-item pipeline), which froze the queue it was meant to
  speed up. The board now ignores subshells when it lists runners.
- **Redacted demo mode** keeps the page's script intact and blocks host names in the host badges; new screenshot
  (`docs/img/jobboard.png`), checked with OCR for every blocked term.
- **By the numbers:** 2,568 recordings and long-file chunks fully speaker-separated (2,015 + 553 chunks), up from 2,483; 37 new
  recordings pulled from two phones today; 243 low-signal pieces of long files re-queued (181 more were silent).
- **Models and tools:** whisper.cpp and the ggml `small.en` model added to the official-links list.
- **Roadmap:** `docs/EARMARK_DUAL_HOST_FAST_HASH.md` (both computers working at once; XXH128 as a fast check at each copy hop,
  SHA-256 unchanged as the custody hash).

## v0.5.5 — 2026-10-02 · overnight numbers, job board order
- **Job board order:** queues with work left are listed first (running, then waiting in a chain, then idle), under a "To do" heading;
  finished queues follow under "Finished", latest finish on top and oldest at the bottom.
- **By the numbers (overnight):** 2,483 recordings and long-file chunks fully speaker-separated (2,010 recordings + 473 chunks), up from 1,960.
  `docs/STATS.md` has a new column; 421 low-signal long-file pieces are not queued yet.
- **Fixed on the GPU host (lesson for anyone running two runners on one list):** when the front and from-end runners reached the same item,
  both submitted it, and the first to finish removed the shared "done" marker, so the other waited forever. The submit step now leaves the
  marker in place, accepts only one written after its own submit, and gives up after 4 hours.

## v0.5.4 — 2026-10-02 · resident-worker queue handling, screenshot
- **Job board screenshot** (redacted demo mode) in the README and `stack/jobboard/README.md` (`docs/img/jobboard.png`).
- **Resident workers:** the board reads an optional spool (`remote_spool_dir`) and shows how many workers have their models loaded, how many items
  are processing and how many wait; items in line show "in line" instead of a time estimate.
- **Labels:** 15-minute pieces of longer recordings show their parent queue and position (e.g. "V29 · piece 15–30 min").
- **README:** resident-worker results (identical output on a 10-file test, 2.6× faster; run one worker on 16 GB and free the GPU cache per item).
- **Analytics chart markers:** "start" is now "AI work begins (Mar 22)"; a new marker at the left edge shows when paid home caregiving was
  approved (paid from Mar 25, 2025, before the chart's June 2025 start). Labels sit on three levels so they do not overlap.
- **By the numbers:** 1,960 recordings and long-file chunks fully speaker-separated (1,782 + 178 chunks).

## v0.5.3 — 2026-10-01 · processing numbers refreshed
- **"By the numbers":** 1,808 recordings and long-file chunks fully speaker-separated (1,681 recordings + 127 chunks), up from 1,488.
- **README and `docs/STATS.md`** brought to Oct 1, 2026 (a new column), including 425 silent or background-sound stretches checked
  against the timeline (counts only).
- **Job board:** ⇧ Priority starts a waiting queue now and holds the other runners until it ends (released automatically, also after a
  board restart).

## v0.5.2 — 2026-10-01 · job board controls, progress bars, capacity guidance
- **Start any queue.** Queues waiting in a chain script get **Start now**; running queues get **Start from end**. The second runner works
  through a reversed copy of the list (`reverse_dir`), and the runners meet in the middle, so at most one item is done twice.
- **Per-runner Pause / Resume and Stop** beside each running job (SIGSTOP / SIGCONT; the item already on the GPU finishes).
  **Pause all** sets every configured pause flag (`extra_pause_flags`).
- **Queue status:** complete / idle rows show first → last finish, time span and items per hour. Items the length guard routed away
  are counted (`long_skip_file`), and Start explains instead of exiting silently.
- **uv-style progress bars** for each item on the GPU. The stage comes from the worker log and cache files (leveling audio, loading models,
  transcribing, separating speakers, naming speakers). Time left comes from a fit on recent items (fixed seconds + seconds per audio
  minute), or their average run time. The bars tick every second.
- **README: how many jobs at once,** measured on a 16 GB card: at most 3 (4 hit CUDA out-of-memory). Chunk recordings over 60 minutes
  into 15-minute pieces, and run one such chunk at a time. Every item's memory peak is the model load, whatever the audio length.

## v0.5.1 — 2026-10-01 · numbers refreshed
- **"By the numbers" updated to Oct 1, 2026:** recordings indexed 2,073 (~760 h); 1,488 fully speaker-separated; 12,572 texts/calls/voicemails
  (incl. 1,756 call/text records read from 3 phones); 14,867 files hashed; 10 device pulls and reads from 5 phones; 55 payroll records exported;
  3,786 h logged vs 2,018 h paid; a 557-day ledger; 36 of 40 stubs exact. Notes, calendar and day counts are unchanged (same account export).
- Version labels on all pages.

## v0.5.0 — 2026-10-01 · local job board
- **New: `stack/jobboard/`.** A local page (127.0.0.1 only) for the GPU transcription queues: GPU host CPU, memory, GPU memory,
  load and temperature; the items on the GPU now, with an estimated progress bar; done/total for every queue; recently finished items;
  runner processes and the queue each one reads; status-only log lines.
- **Controls:** pause, resume, start a queue, stop a runner. Each call needs a per-run token and a localhost Host header. Queues that a
  running chain script will start on its own can't be started twice. `--dry-run` shows the command instead of running it.
- **Automatic cleanup** of the GPU host's staging copies of finished or abandoned items, only when no worker uses them (never originals).
- **Per-queue notes and report links** come from local files named in the git-ignored config; Markdown reports render as formatted pages (pandoc).
- **Redacted mode** (`--redact`) blocks out names and identifiers from a local list for demos.
- **Highlighted queues:** an optional registry field marks queues whose results need review (e.g. ⚖ legal lead · party).
- **Public example:** `docs/examples/case-job-history.example.html` (roles and categories, redacted) and `stack/jobboard/redact_file.py`.
- **Requirements:** `stack/requirements/jobboard.txt`. Standard library only (Python 3.11+); pandoc, ssh and ffprobe are optional tools.

## v0.4.3 — 2026-09-30 · SDS context with official sources
- **New section: "Who holds which piece of the record".** It explains the roles in self-directed Medicaid care (the member as
  employer, the managed care organization, the fiscal employer agent, the county, the caregiver) and the gap between them.
  It uses roles only and names no agency or company.
- **Government citations only:** Medicaid.gov Self-Directed Services; Wisconsin DHS P-00088N and P-00593; the WI DHS IRIS page;
  the WI DHS member rights and appeals page. Every link was checked (medicaid.gov was confirmed by fetch, because it blocks scripted checks).

## v0.4.2 — 2026-09-30 · citation
- **AgentsView cited:** every mention now links to https://github.com/kenn-io/agentsview, the local-first session index
  used to check breakthrough citations (session IDs). README lists it too.

## v0.4.1 — 2026-09-30 · name, lab links, license
- **Name:** phone-net · I.C.K.S. (phone + net + I.C.K.S.). The page header now reads "phone⁺net⁺tics · let your phone talk to
  you", with small plus signs.
- **The larger µlab:** a new section links the sibling public repos and their pages (ai-gateway, mok-tua, fast-models,
  grok-tua-tok-tua, johnny-appleseed-chipper, aida-complex-doc-lab, ada-doc-check, cmip-terpene-db,
  all-in-one-home-food-bank-tank-rank, shreddit).
- **Footer:** every page now has the same µ mark as the sibling pages: "one door in a larger µlab · © 2026 M.A.N.A.G.E.R. LLC",
  with links to source, README, Changelog and MIT.
- **MIT License** added (`LICENSE`), matching the sibling repos.

## v0.4.0 — 2026-09-30 · public release
- **Public.** The repo is public and the pages are hosted on GitHub Pages (`site/` deployed by `.github/workflows/pages.yml`).
  Before the switch, every file in all 18 earlier commits was scanned for names, addresses, phone numbers, emails, agency and
  facility names, local paths, hostnames and keys. None were found, and there are no binary files in the history.
- **Breakthrough: a self-healing overnight GPU chain.** Stages are now resumable and gated per item on GPU memory, with a pause file.
  A second AI agent (Grok Build) added a silent watcher: it reports only failures or completion, relaunches a dead chain once, and
  latches on VRAM, memory, SSH or stalls. The chain ran unattended overnight: 159 of 882 deep-inspection files, plus a
  marker-correlation stage.
- **Second-device intake.** 39 new recordings from a second phone (Sep 26–29) were queued and 35 processed. Three unreadable WAV
  files are logged as custody items and left unrepaired.
- **Primary-source rule.** A figure that comes from an AI summary is written as "our notes refer to" until it is checked against
  the primary record. This caught two errors before they reached a letter: a pay stub's service period, and the date a handout
  was received.
- **Proof of delivery.** Fax-service confirmations are cross-checked against sent mail, to show which document actually went where.
  This corrected one claim before it went into a letter.
- **Consent-first packet workflow.** The person the records are about hears or reads each letter before signing, and approves
  letter by letter. Phone participation is recorded as a note, not a signature. Requests are split by recipient and purpose
  (records, payroll, a communication accommodation). Appeal deadlines are tracked separately from records requests. A second AI
  assistant reviews the wording before anything is signed.
- **Session index repaired.** A sync failure in the local session index was isolated to one provider and bypassed, so breakthrough
  citations stay checkable.
- Stats refreshed (`docs/STATS.md`). Version labels on every page updated; "private placeholder" labels removed.

## v0.3.1 — 2026-09-29 (private) · source attribution fix
- **Breakthrough citations corrected.** The 2026-04-14 and 2026-06-19 entries were labeled ChatGPT, but both were grok.com chats. The
  session index had filed early grok.com conversations as ChatGPT; each citation is now checked against three independent records
  (session index, Grok export, chat-history import).
- 2026-04-14 now cites grok.com chat `a368cd55` (first build question). 2026-06-19 now cites grok.com chat `7dc00839` (catalog naming,
  00:01) with commit `ee882c1` (00:52); the coding agent for that commit was not recorded and is marked so.
- The other eight citations were re-verified (3 Codex, 5 Claude Code).

## v0.3.0 — 2026-09-29 (private) · payroll sniff level-up
- **Workflow page** (`site/workflow.html`): phone → USB-C → local black box with four stages and every model/tool linked; cloud assistants
  shown outside the box as "code only".
- **Payroll truth from the payroll app itself:** breakthrough entry for the payroll company's shift exports and the first read-only on-device
  audit of the payroll app. Groundwork for `cut.glass`.
- **Official links** for all models, tools and AI assistants.
- **Scrubbed:** no working-repo names, local paths, hostnames or account names; config example uses placeholders.

## v0.2.0 — 2026-09-29 (private)
- **Full analytics page** (`site/analytics.html`): aligned daily strips for care notes, emergencies, safety incidents, AI sessions, and commits
  per project; AI-agent incident (CVE-FAUX) dots with agent letters and a zoomed panel; AI usage around hard days (cloud assistants vs local
  gateway tokens); notes-per-day vs hours-covered scatter against the paid cap.
- **Hours chart uses the payroll company's own exports** (logged in app vs paid cap, 535 service days). Removed "4.4 h", a spoken estimate
  that was never a paid cap. Caps: 3.5 → 4.0 → 4.25; Sep 5.25 sent vs 6.5 promised.
- **Summary page:** breakthroughs timeline with commit and session citations; computer-side caregiving time; emails split by sender;
  incident-day counts (incidents, not mentions); totals and methods.
- **cut.glass earmark:** consent-based, read-only device audit of a caregiver app (first real run on the payroll app).
- Stack: docker compose, per-part requirements, BUILD.md.

## v0.1.0 — 2026-09-29 (private)
- Skeleton: README, pipeline, models and approvals, stats, privacy rules, config template, placeholder page.
