# Earmark: cut.glass — "check the wire, see the truth" (module, later)

**Idea:** one command that, with the device owner's consent, reads what a phone itself already records about a specific app
(timekeeping, portal, messaging) and turns it into a short, checksummed findings page. It saves the caregiver the brainpower and the
legwork, and it replaces arguing about what happened with what the device logged.

**First real run (2026-09-29, payroll app, read-only over USB):** version and install/update dates, granted permissions (location while in
use; no camera/mic), last location + biometric use (clock-in time), foreground/background state, screen time per day/week/month/year, and
crash/not-responding reports. Took under a minute and needed no root.

## What it reads (Android, `adb`, no root)
`dumpsys package <pkg>` · `cmd appops get <pkg>` (last access to location/camera/mic/biometric) · `dumpsys usagestats` (events ~days;
totals daily→yearly) · `dumpsys activity` (foreground, services) · `dumpsys dropbox` crash/ANR + `logcat -b crash` (short retention) ·
`dumpsys notification` · device model/SKU/build.

## Rules (legal and honest)
- Only the caregiver's own device, with the device owner's consent. Read-only: never tap, stop, clear or modify the app.
- No root, no bypassing app security, no reading another app's private data, and no intercepting network traffic.
- Everything is timestamped and hashed at capture; the findings page cites the raw file for every line.
- Retention limits are stated, not hidden (for example, "crash logs are kept for days, so older lockups have aged out").
- The output feeds a **written request** for the company's own records (for example, the EVV audit log). It doesn't replace one.

## Build later
`cut.glass <package> [--out DIR]` → raw captures + SHA256SUMS + FINDINGS.md. Presets for common caregiver apps (timekeeping/EVV, patient
portal, pharmacy). A scheduled mode that snapshots usage totals weekly, since the phone keeps detailed events only for a few days.
