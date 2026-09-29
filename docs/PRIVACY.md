# Privacy rules (non-negotiable)

**Never commit:** audio, video, photos, transcripts, summaries, embeddings, indexes, emails, letters, scans, names,
phone numbers, addresses, dates of birth, account numbers, medical details, or case vocabulary (people's names in
keyword lists).

**Allowed:** code with paths and names read from `config/icks.yaml` (git-ignored), templates, aggregate counts,
and synthetic test data.

**Before any push:** run a PII scan and read the diff. Public release only after counsel confirms nothing
case-specific leaks.

**Sharing is always a human decision.** The tool never uploads, emails, or publishes on its own.
