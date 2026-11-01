# TODO

## Evidence custody (ISO/IEC 27037 alignment), added 2026-10-07

phone+net+I.C.K.S. is a **self-collected evidence record**. The items below were checked against ISO/IEC 27037 (initial handling of digital evidence), with 27041 (method validation), 27042 (analysis), 27043 (process) and 27050 (e-discovery) as support. This is a self-assessment, not a certification.

### Goals: keep these (already solid)
- [x] **Hash at acquisition.** SHA-256 manifest for every pull, written at copy time. Spot re-checks pass (2026-10-07: 55/55 and 41/41).
- [x] **Originals separate from work.** Each pull lands in its own device- and date-named folder; analysis runs on copies.
- [x] **Facts separate from interpretation.** Machine transcripts and captions are labelled unreviewed; identity claims are the subject's statements; inferences are marked.
- [x] **Local processing for sensitive data.** Transcription, speaker separation, captions and embeddings run on local hardware; health data never goes to a cloud service.
- [x] **Written method.** Collect → fix custody → disaggregate → label → analyze → aggregate for release → keep the link (white paper §6).
- [x] **Volatile data first.** Cloud-expiry dates and the day's key recording set the order of work.
- [x] **Known failure modes on record.** Each process mistake is written up with its fix, so it is not repeated.

### To do: close the gaps (in this order)
- [ ] **Custody log.** Append-only JSONL with one event per acquire / transfer / derive / verify / analyze / disclose. Each event records who, when, host, tool and version, path, and SHA-256. Ship a generic `scripts/custody_log.sh` with a config path (no case paths in the repo).
- [ ] **Derived files point to their parent.** Repairs, 15-minute chunks, app exports and transcripts carry `parent_sha256`.
- [ ] **Read-only pulls.** `chmod -R a-w` each pull folder after hashing. Working files (catalogs, queues) are versioned, never rewritten in place.
- [ ] **Live-acquisition notes.** Each pull README says "live logical acquisition" and lists the device-state changes (screen woken, app opened, no data written) and the tool versions.
- [ ] **AI agents as logged tools.** Local models are logged with name and version. A `cloud_view` event, with the session ID, records any content that reached a cloud model.
- [ ] **Device and source register.** One CSV covering device serials, cloud accounts, time basis (UTC vs local) and storage encryption state.
- [ ] **Method validation (27041).** A known-answer test for hashing, and a hand check of 3 transcript samples (word errors, speaker-label errors).
- [ ] **Scheduled verify.** A periodic `shasum -c` over all manifests, logged as `verify` events.
- [ ] **Disclosure record.** Every outside send (fax, email, packet) logs the exact file hash.
- [ ] **Production export (27050).** Item + hash + its custody-log lines, on request from counsel.
- [ ] **Second check.** State that one person collects and analyses; before production, have a lawyer or second person re-verify the key hashes.
- [ ] **Job board panel.** Show custody-log counts and the last verify result next to the queues.

Optional background for the white paper's release rule: ISO/IEC 27045 (big data security and privacy; draft). Its aggregation, inference and re-identification risks support "aggregate the disclosure". This is not a compliance claim.

## Earmarks (2026-11-01, GREEK SQUAT v0.8.0)
- **Android app (APK):** GREEK SQUAT in a pocket. One Android phone saves another over a USB-C OTG cable (adb host over libusb):
  texts, calls, contacts, calendar, storage, voicemail through Share, then the status screen on both phones. Local models where the
  phone can (speech-to-text, small vision captions, embeddings). Overlay badge (draw over other apps) for background jobs.
- **iOS app:** status and capture only (iOS cannot pull another device). Shows a running pull from the home computer over the LAN,
  records stories, and hands files to the desktop app.
- **Desktop app signing:** still unsigned (cost); revisit if a grant or sponsor covers it.

## Earmark (2026-11-01): ALL YOUR PAPES ARE BELONG TO US edition ("THE PAPE")
The head of the paper scroll order. The phones are saved; now the paper trail joins the paper parade.
- **Hardware:** a used Fujitsu ScanSnap S1500M (Mac edition, duplex sheet feeder). Driver path is the free, open-source
  SANE `fujitsu` backend (`brew install sane-backends`, `scanimage`). No vendor account, no cloud.
- **Flow:** stack of paper → duplex scan → `ocrmypdf` (local Tesseract) → searchable PDF + SHA256SUMS + custody line,
  same folder and log format as a phone pull, so the job board and the on-phone status screen show it (pages k/N).
- **Desktop app:** a "Scan paper" card next to "Pull new files": scanner model, Re-identify, Scan button, page count.
- **Sort, don't read:** filename by date and sender from the OCR'd first page; anything medical stays local (PHI rule).
- **Puns welcome:** Pape Bull (the release note), Paper Infallibility (the checksum), Habemus Papyrum (the finish screen).
- **P.A.P.E. = Paper Accessibility, Parsing & Evidence.** Accessibility: every scan comes out a searchable, readable PDF and
  gets an ada-doc-check pass (WCAG 2.1 AA first-pass triage; tagged PDF/UA and alt text later). Parsing: Tesseract/ocrmypdf
  first, then a vision OCR model for hard pages, then a small local model for "what is this". Evidence: hashes, custody line,
  originals kept, git history for anything public.
- **Why (the want):** a public-college Digital Accessibility Specialist listing (2024 web accessibility rule, WCAG 2.1 AA,
  audits of PDF/Word/PowerPoint, remediation, training, progress reporting) reads like P.A.P.E.'s job description.
  Reuse, don't rebuild: `ada-doc-check` (score, triage, fail closed), `aida-complex-doc-lab` (multi-document harness, scrubber),
  `ocr-tua` (OCR/vision test service). Add: per-scan accessibility report, page count / words / time stats.
- **Smoke test 2026-11-01 (local):** scan + Tesseract 22-53 s per stack; blank backs set aside; rotation threshold lowered
  (upside-down pages scored 12-15, under the default 14). Vision OCR on a single listing page: glm-ocr 139 s (clean text),
  deepseek-ocr 95 s (layout boxes + tables). Context: gemma4:12b with thinking off 117 s; the 4B translation model ignores
  instructions, so don't use it as the clerk.
- **Signup kits:** any handout for an online signup (care agency, hospice, county) becomes a kit: plain HOWTO from the paper,
  official pages snapshotted with hashes (C.H.I.P.P.E.R. manifest), an update log per fetch (C.H.A.I.N.S.), git diff when a
  page changes. Johnny Appleseed indexes the kits. Never stores passwords or codes. Stays a how-to: the person signs up.
- **Way later: port Unlimited-OCR (Baidu, 3.3B, MIT) off CUDA.** As shipped it needs NVIDIA (`.cuda()`, bf16, sglang
  wheel): fits MRGPU 16 GB, not the Tower P2000 (5 GB, Pascal has no bf16). Port targets: Mac (MPS, fp16) and Xeon (CPU,
  int8). glm-ocr already runs on the P2000 and the Mac in the meantime. Community ports exist to try first:
  `FluidInference/unlimited-ocr-mlx-coreml` (Mac) and `sahilchachra/Unlimited-OCR-GGUF` / `AtomicChat/Unlimited-OCR-2-GGUF` (llama.cpp).
- **OCR bake-off candidates (Nov 2026, self-reported scores):** PaddleOCR-VL-1.6 and MinerU2.5-Pro (OmniDocBench top),
  Chandra OCR 2 (olmOCR-Bench top), GLM-OCR (installed), DeepSeek-OCR (installed), MiniCPM-OCR-1.0 (GGUF), Xiaomi-OCR-0,
  Falcon-OCR, surya-ocr-2.5. Score them on our own scans (word recall vs a hand-checked page, time, memory) before picking.
- **Accessibility tools the listing names that P.A.P.E. doesn't cover yet:** veraPDF (PDF/UA check; installed on the Mac,
  not wired), tagged-PDF output (ocrmypdf makes untagged PDFs: render OCR'd markdown to HTML, print a tagged PDF with headless
  Chromium, then veraPDF), axe-core / Pa11y (open stand-ins for WAVE and axe DevTools on web pages), Word/PowerPoint checks
  (headings, alt text, reading order via python-docx / python-pptx), local alt text from a vision model, and a screen-reader
  pass (VoiceOver on the Mac; NVDA/JAWS are Windows-only, manual). Color contrast and alt-text fields already exist in ada-doc-check.
- **Fold in A.I.D.A. (grokcode `agents/aida/`, reuse, don't rebuild):** `layman_relay` (dual-audience plain-language
  briefs: caregiver actions + gentle bullets for the person receiving care; pulls dates and money amounts) for every scan
  and signup kit · `assurance` (Section 508 / WCAG 2.1 AA / PDF/UA deep pass, fail-closed approver) after veraPDF ·
  `document_accessibility_gate` (checksum + accessibility score before anything is filed) · `aida_pdf_bridge`
  (ocrmypdf queue) · `manager/ingestion/caption_rag` (local VLM captions = alt text for figures in the tagged PDF) ·
  V.O.X. + Kokoro TTS on MRGPU (read any scan aloud: an audio copy for low vision) · `video_scan` for video evidence.
- **Email formatting check (P.A.P.E. for inboxes):** same audit for HTML email bodies: images without alt, layout tables,
  fixed widths (no reflow on phones), tiny footers, "click here" links, content only inside a PDF attachment.
- **Speech side (not OCR):** NVIDIA Nemotron-3.5-Transcribe-30B-A4B as a second-opinion transcriber next to WhisperX
  (two-model agreement). Full model too big for MRGPU 16 GB / Mac 24 GB; try the small variants
  (`akhaliq/nemotron-3.5-transcribe-mini-64e`, `FluidInference/nemotron-3.5-transcribe-lite-coreml`) or a 4-bit GGUF with MoE
  experts on the CPU. Cloud providers exist but care recordings stay local.
- **Windows edition (later): old laptop, WSL Ubuntu, one-click install.** Draft, untested: `grokcode/scripts/windows/
  pape_install_wsl.ps1` (turns on WSL, installs Ubuntu, usbipd-win for the USB scanner) + `pape_install_wsl.sh` (CPU-only kit).
  Low-power smoke test 2026-11-01 (Mac, CPU only, 2 threads, 6 scan pages): Tesseract 0.9 s/page; RapidOCR (PP-OCR in ONNX,
  ~15 MB) 5.2 s/page with 95% agreement both ways. Plan: Tesseract + RapidOCR, and a page goes to a vision model only
  where the two disagree. Tiny vision models (MinerU2.5-Pro 1.2B, Xiaomi-OCR-0, PaddleOCR-VL 0.9B) are next once they download.
- **Blank-back threshold:** a legal packet still let 3 near-blank backs through at 0.2% ink; also treat "OCR words < 5" as blank.

## Earmarks (2026-10-16, local)
- **Fax tooling:** compare FaxZero (current; $3.29/send, 25-page cap, confirmation email per job) with alternatives that give a delivery
  report per page and an API or CLI: e.g. eFax / HelloFax / Fax.Plus / iFax / SRFax; check price per page, HIPAA BAA, inbound fax
  number, and whether confirmations can be pulled into the custody log automatically.
- **Billing transparency logins (owner sets them up; agent never stores credentials):** Medicare account (medicare.gov, Blue Button
  claims export), Wisconsin Medicaid / ForwardHealth member portal, Social Security (my Social Security: benefit letter, premium
  deductions), and the care-plan company's and payroll company's portals. Goal: export claims and billing for the care-plan company,
  hospice and payroll company, and reconcile them against care logs. Exports go to the private evidence folder, hashed on arrival.
- **Procurement (2026-10-26): sheet-fed (ADF) scanner for paper intake.** Bought used: Fujitsu ScanSnap S1500M, $33.97 (online
  thrift auction; USB cable on hand). Purpose: receipts, letters, agency packets, invoices, orders and handwritten notes come in as
  paper; the flatbed was broken, and a phone camera app is too slow for whole packets. Plan when it arrives:
  1. An always-on Linux box (old laptop, or USB pass-through on the storage or GPU host) runs SANE (`fujitsu` backend) and
     `scanbd`, so pressing the scanner's button starts a scan with no screen needed.
  2. Each scan lands as a PDF in a watch folder, hashed on arrival (same custody log as phone pulls), then `ocrmypdf` adds text.
  3. Tiered OCR check, all local: OpenCV for deskew and cleanup only; Tesseract 5 plus a second engine (PaddleOCR or docTR); a
     local vision model referees pages where the engines disagree. Each page gets a grade (A/B/C/F) from cross-engine agreement and
     field checks (dates, amounts, phone numbers). Grade C/F pages are flagged for a person to check.
  4. Sorting: the type (receipt, letter, invoice, order, handwritten note) and its dates go into the catalog, so paper sits on the
     same timeline as recordings and email. Private pages follow the same rules as recordings: local only, counts only in public.
