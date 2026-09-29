# phone-net · I.C.K.S.

**Intake · Custody · Keywords · Synthesis** (working expansion; rename freely)

Skeleton outline (2026-09-29). A local-only toolkit for family caregivers: turn the recordings, emails and letters on
your **own** phone into an indexed, checksummed, searchable record, so you can ask care agencies precise questions in
writing and show how each answer was found.

> **Private repo.** Code, config templates and aggregate stats only. **No PII, no PHI, no recordings, transcripts,
> names or case details, ever.** See `docs/PRIVACY.md`.

## Outline
- [ ] **Intake**: USB-C pull (`adb`), diff against earlier backups by name+size, size/SHA-256 verify
- [ ] **Custody**: checksums on every copy and output; true dates from audio metadata when file dates are copy days
- [ ] **Keywords**: level → transcribe (WhisperX) → speakers (pyannote + own voiceprints) → keyword sweep → meaning search
- [ ] **Synthesis**: local summaries, dated index, audience-tiered packets, methods note

## Files
| Path | Purpose |
|---|---|
| `docs/PIPELINE.md` | stages and lessons (outline) |
| `docs/MODELS_AND_APPROVALS.md` | free tools, models, Hugging Face gated approvals |
| `docs/STATS.md` | aggregate numbers from the first run (no PII) |
| `docs/PRIVACY.md` | what never goes in this repo |
| `config/icks.example.yaml` | paths/hosts template (real `icks.yaml` is git-ignored) |
| `site/index.html` | placeholder single page for a later public release |
| `scripts/` | empty until working scripts are ported **after sanitization** |

Port order and design notes live in the owner's private working notes; see `docs/PIPELINE.md` for the summary.
