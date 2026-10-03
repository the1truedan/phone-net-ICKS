# Changelog

## v0.5.10 — 2026-10-03 · new numbers, two new breakthroughs
- **By the numbers:** 2,290 recordings indexed (every phone pull, checked by hash); 3,172 recordings and long-file chunks fully speaker-separated
  (2,097 + 1,075 chunks), 274 more queued; 90 emails indexed; 560 days in the day-by-day ledger.
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
