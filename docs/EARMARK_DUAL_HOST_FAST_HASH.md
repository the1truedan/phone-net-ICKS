# Earmark: two computers working at once, and a fast first hash (v0.5.6)

**Goal:** finish each day's recordings sooner by giving both computers work at the same time, and make every copy hop
cheap to check, without weakening the custody record.

## Where things stand (v0.5.6)
- **GPU host (Linux, 16 GB card):** the deep pass. Large transcription model, word timing and speaker separation run in one
  resident worker that keeps its models loaded. One worker is the limit on this card: two workers ran it out of memory.
- **Mac (Apple silicon):** cuts long recordings into 15-minute pieces, checks each piece for silence, uploads pieces to the
  GPU host, and since v0.5.6 runs a **quick first pass** with a small model ([whisper.cpp](https://github.com/ggml-org/whisper.cpp),
  `small.en` q5_1) on its own GPU. About 10 seconds per 15 minutes of audio.
- The quick pass scores each piece with the same case-term list and tier rule as the older first-pass tiers: pieces with case
  terms or real conversation go to the deep pass; the rest are listed for a deep pass later. **Nothing is dropped.**
  First run on a 16-hour recording: 12 of 65 pieces needed the deep pass, saving about an hour of GPU time.
- The job board shows both computers under **Active jobs**, with CPU, GPU and network per host and a saturation line.

## Next (not built yet)
1. Move audio leveling and the silence check fully to the Mac, so the GPU host only receives pieces that are ready.
2. Let the Mac transcribe short items itself when the GPU host is busy (small model first; deep pass later if a case term appears).
3. A capacity rule on the board: start Mac-side work only while the shared 1 GbE link and the Mac GPU have headroom.
4. Keep the quick pass honest: a small model misses quiet speech and names more often, so a "later" piece must stay visible
   and easy to re-queue (the board's tier C queues already do this).

## Fast first hash (held for later)
- **Today:** SHA-256 at the first pull from the phone is the custody hash. Measured on one core: Apple M4 about **3.0 GB/s**
  (hardware SHA-256), the storage server's Xeon E5 v3 about **0.41 GB/s** (no SHA instructions). Intake is limited by the
  phone/USB read and the 1 GbE link (about 110 MB/s), not by hashing.
- **Earmark:** add [xxHash](https://github.com/Cyan4973/xxHash) **XXH128** (128-bit, not the 64-bit XXH3) in the **same read**
  as SHA-256 at the pull, then check only XXH128 at each later hop (USB → Mac → storage server). The storage server re-verifies
  SHA-256 in the background at idle priority.
- **Rule that does not change:** XXH128 is not cryptographic. It speeds up transfer checks; it never replaces SHA-256 in the
  custody record, and SHA-256 is always taken at the first point of custody, not later on the server.
- Use the upstream xxHash project (`xxhsum -H2`), not a fork.
