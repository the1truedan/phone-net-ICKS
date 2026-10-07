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

## Earmarks (2026-10-16, local)
- **Fax tooling:** compare FaxZero (current; $3.29/send, 25-page cap, confirmation email per job) with alternatives that give a delivery
  report per page and an API or CLI: e.g. eFax / HelloFax / Fax.Plus / iFax / SRFax; check price per page, HIPAA BAA, inbound fax
  number, and whether confirmations can be pulled into the custody log automatically.
- **Billing transparency logins (owner sets them up; agent never stores credentials):** Medicare account (medicare.gov, Blue Button
  claims export), Wisconsin Medicaid / ForwardHealth member portal, Social Security (my Social Security: benefit letter, premium
  deductions), and the care-plan company's and payroll company's portals. Goal: export claims and billing for the care-plan company,
  hospice and payroll company, and reconcile them against care logs. Exports go to the private evidence folder, hashed on arrival.
