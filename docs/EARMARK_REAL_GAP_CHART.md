# Earmark: real "care vs. hours vs. pay" chart (smoke test, later)

**Goal:** replace the page's illustration with the real trajectory: approved hours over time, doctor visits per week,
and hours actually paid. Real data stays **private** (it is health information). A public version, if ever, is
anonymized and aggregate only.

## Data already on hand (no new collection needed)
- Approved hours/day at each change point (visit and call transcripts, care-manager email): early ~3.5 → ~4.25/4.4 → 6.5 from the start of a month.
- 27 doctor-visit dates entered as separate payroll lines (one email, Apr–Aug).
- Timesheet/pay notes (e.g., one processed timesheet short five days), plus the payroll history once the locked secure message is opened.

## New data: patient-portal visit history
Order of preference (least fragile first):
1. **Official export** from the portal's web app: "Download my record" / health summary (C-CDA XML) or the past-visits
   list printed to PDF. Parse locally.
2. **Records request** to the clinic, if the export lacks visit dates.
3. **Screen automation (scrcpy + adb) of the phone app**, last resort: fragile, slow, and it breaks when the app updates.

**Consent:** only with the member's own login and her explicit OK (or a legally activated POA). Everything stays on
local disk. Nothing goes into this repo.

## Smoke test (when ready)
1. One month of portal visits → CSV (date, type). Compare against the payroll visit lines for that month.
2. Plot three series for that month: visits, approved hours, paid hours.
3. If it matches reality, extend to June 2024 → now.

Output: a private chart for the counsel/advocate packet. The public page keeps the illustration unless everything is
anonymized and counsel agrees.
