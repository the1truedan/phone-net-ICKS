# Changelog

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
