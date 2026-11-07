# MyChart export: save a loved one's chart to your own disk, then ask it questions

Runbook for re-running the MyChart export and searching it. Written 2026-11-07 after a family needed a dietitian's
notes ("does not like regular Ensure") to answer an insurer's billing. Local only: nothing is uploaded.

## What gets saved
| Lane | What | How |
|---|---|---|
| A. Visit documents | After Visit Summaries (AVS) and progress notes (dietitian, oncology, palliative) as PDFs | The MyChart Android app on a USB-connected phone, driven by adb: one pass over Visits > Past, and for each listed visit: More options > Print > **destination must read "Save as PDF"** (else abort; never send to a printer) > Save. PDFs land in the phone's Download folder, then are pulled and hashed. |
| B. Full record | MyChart's own "Download / Request my record" export (medical history, documents) | Requested in MyChart, saved as delivered, then unpacked to text. |

Each PDF is copied, SHA-256 hashed into `SHA256SUMS.txt`, logged in `custody_log.txt`, and turned into text
(`pdftotext -layout`; images get OCR). Text can be embedded (bge-m3) for search.

## One place for every export (the rule)
All exports live under **one root**, set once:
```
~/phone-net-ICKS/pulls.json   →   "exports_root": "/Volumes/<backup disk>/backups/_exports"
<exports_root>/mychart/<person>/<YYYY-MM-DD>/
    pdf/   txt/   SHA256SUMS.txt   custody_log.txt   targets.tsv   run.log
```
No more one-off folders inside case folders. Anything older is linked in, not moved, so custody paths stay valid.

## Re-run (today's scripts, until the app button exists)
1. Phone: USB connected, unlocked, MyChart open on **Visits > Past**. Never type the PIN for the owner.
2. Make the target list (`targets.tsv`: date, reason, exact card text).
3. Run the batch; it exits 4 if the phone is not on the Visits list.
4. Pull + hash the new PDFs; convert to text; optional: embed.
5. Check: count PDFs against targets. **Never trust "end of list" or "finished N/M" alone**: a batch once reported done
   with 0 new PDFs because the phone had left the Visits list.

Gotchas seen: unread cards read `Unread\n<label>` (newline) on some app versions, so labels are normalized before matching;
MyChart drops the "Unread" prefix once a visit is opened elsewhere.

## Ask the export
Search the text for a word and its context (example: a supplement the person disliked):
```
grep -i -n -E "ensure|boost|dietitian|too sweet" <exports_root>/mychart/<person>/*/txt/*.txt
```
Planned: the desktop app's existing "Ask your records" box (local Ollama model, `ask_records`) will read this folder,
so a family member can type a question and get the dated lines back, each with its file and date.

## Planned in the app (v0.9)
- "Export MyChart" button: runs lanes A and B into `exports_root`, with the progress page on the phone.
- "Ask the export": question in, dated quotes out, file + page cited; never paraphrases a clinical note.
- Re-run picks up only visits newer than the last export (by date and card text).
