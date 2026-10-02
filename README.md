# phone-net · I.C.K.S.

**(phone + net + I.C.K.S.)** · phone<sup>+</sup>net<sup>+</sup>tics · *let your phone talk to you*

**Intake · Custody · Keywords · Synthesis**

**Live page:** https://the1truedan.github.io/phone-net-ICKS/ · v0.5.3 (2026-10-01) · public since 2026-09-30 · MIT

A local-only toolkit for family caregivers. It turns the recordings, emails and letters on your **own** phone into an indexed, checksummed, searchable record. With that record you can ask care agencies precise questions in writing, and show how each answer was found.

It was built by one caregiver, between shifts, with AI coding assistants writing the code and every recording staying on local hardware.

> **What is in this repo:** code, config templates, pages and aggregate numbers only.
> **What never is:** recordings, transcripts, names, addresses, case details, or anyone's health information. See `docs/PRIVACY.md`.

## Job board (v0.5.0, updated v0.5.3)
A local page (127.0.0.1 only) to watch and steer the GPU transcription queues: GPU host CPU/memory/GPU and temperature,
items on the GPU with uv-style progress bars (real stage + time left), Start now / Start from end for any queue, Pause/Stop per runner, done/total per queue, recently finished items, pause/resume/start/stop, automatic
cleanup of abandoned staging copies, highlighted queues (e.g. ⚖ legal lead), and formatted local reports.
Standard library only. See `stack/jobboard/README.md`, `stack/requirements/jobboard.txt` and the public-safe example
`docs/examples/case-job-history.example.html`.

## What it does

| Stage | What happens |
|---|---|
| **Intake** | USB-C pull from the phone (`adb`), diff against earlier backups by name and size, then verify size and SHA-256 |
| **Custody** | Checksums on every copy and output. True recording dates are recovered from audio metadata when file dates are only copy dates |
| **Keywords** | Level the audio, transcribe it (WhisperX), label speakers (pyannote plus your own voiceprints), run a keyword sweep, then meaning search |
| **Synthesis** | Local summaries, a dated index, packets tiered by audience (family, care team, advocate, counsel), and a methods note |

## By the numbers (2026-10-01)

2,073 recordings indexed · ~760 hours transcribed on local hardware · 1,808 recordings and long-file chunks fully speaker-separated · 425 silent or background-sound stretches checked against the timeline · one 16 GB GPU, up to 4 jobs at once. Full table: `docs/STATS.md`.

## Pages

| Page | What it shows |
|---|---|
| [`index.html`](https://the1truedan.github.io/phone-net-ICKS/) | Summary, breakthroughs timeline, totals and methods |
| [`analytics.html`](https://the1truedan.github.io/phone-net-ICKS/analytics.html) | Daily strips: care notes, emergencies, AI sessions, commits, hours vs the paid cap |
| [`workflow.html`](https://the1truedan.github.io/phone-net-ICKS/workflow.html) | From the phone to the local "black box", with every tool linked |

## Files

| Path | Purpose |
|---|---|
| `docs/PIPELINE.md` | Stages and lessons |
| `docs/MODELS_AND_APPROVALS.md` | Free tools, models, and the Hugging Face gated approvals |
| `docs/BUILD.md`, `stack/` | Docker compose and per-part requirements |
| `docs/STATS.md` | Aggregate numbers (no PII) |
| `docs/PRIVACY.md` | What never goes in this repo |
| `docs/EARMARK_*.md` | Next modules: `cut.glass` (a consent-based, read-only audit of a caregiver app) and the real hours-gap chart |
| `config/icks.example.yaml` | Paths template. The real `icks.yaml` is git-ignored |
| Session history | Breakthrough citations are checked against a local [AgentsView](https://github.com/kenn-io/agentsview) index |
| `CHANGELOG.md` | What changed in each version, including the breakthroughs |

Working scripts are ported into `scripts/` only after sanitization.

## Self-directed services: official sources

The page explains the roles (the member, the managed care organization, the fiscal employer agent, the county, the caregiver) without naming any organization. Sources:
[Medicaid.gov: Self-Directed Services](https://www.medicaid.gov/medicaid/long-term-services-supports/self-directed-services) ·
[WI DHS SDS FAQ, P-00088N](https://www.dhs.wisconsin.gov/publications/p0/p00088n.pdf) ·
[WI DHS SDS in Family Care, P-00593](https://www.dhs.wisconsin.gov/publications/p0/p00593.pdf) ·
[WI DHS IRIS](https://www.dhs.wisconsin.gov/iris/index.htm) ·
[WI DHS member rights and appeals](https://www.dhs.wisconsin.gov/familycare/fullpartner.htm)

## The larger µlab (M.A.N.A.G.E.R. LLC)

phone-net · I.C.K.S. is one door in a larger µlab. The sibling public repos:

| Repo | Page | What it is |
|---|---|---|
| [ai-gateway](https://github.com/the1truedan/ai-gateway) | [page](https://the1truedan.github.io/ai-gateway/) | Home LLM gateway: routes models across machines. The local gateway these pages refer to |
| [mok-tua](https://github.com/the1truedan/mok-tua) | [page](https://the1truedan.github.io/mok-tua/) | Script → storyboard stills → optional video, on your own GPU |
| [fast-models](https://github.com/the1truedan/fast-models) | [page](https://the1truedan.github.io/fast-models/) | Two spare NVMe drives turned into one fast, deduped model pool |
| [grok-tua-tok-tua](https://github.com/the1truedan/grok-tua-tok-tua) | [page](https://the1truedan.github.io/grok-tua-tok-tua/) | Coding CLIs next to a live health and spend pane |
| [johnny-appleseed-chipper](https://github.com/the1truedan/johnny-appleseed-chipper) | [page](https://the1truedan.github.io/johnny-appleseed-chipper/) | Artifact manifests (C.H.I.P.P.E.R.S.) and custody receipts (C.H.A.I.N.S.) |
| [aida-complex-doc-lab](https://github.com/the1truedan/aida-complex-doc-lab) | [page](https://the1truedan.github.io/aida-complex-doc-lab/) | A.I.D.A. complex-document accessibility harness |
| [ada-doc-check](https://github.com/the1truedan/ada-doc-check) | – | Prepare-only ADA/WCAG-style document triage |
| [cmip-terpene-db](https://github.com/the1truedan/cmip-terpene-db) | [page](https://the1truedan.github.io/cmip-terpene-db/) | Schema ideas for cannabis and hemp chemistry |
| [all-in-one-home-food-bank-tank-rank](https://github.com/the1truedan/all-in-one-home-food-bank-tank-rank) | – | Local-first home food bank |
| [shreddit](https://github.com/the1truedan/shreddit) | [Greasy Fork](https://greasyfork.org/en/scripts/589405-shreddit) | Userscript: modern Reddit as a wide, fast reading view |

## License

[MIT](LICENSE) · © 2026 M.A.N.A.G.E.R. LLC
