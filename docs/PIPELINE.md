# Pipeline (outline)

| # | Stage | Tools | Notes from the first run |
|---|---|---|---|
| 1 | Phone delta pull | adb, shasum | Inventory `/storage/emulated/0` + SD card (not `/sdcard`, a symlink `find` won't enter); pull only the gap; verify size |
| 2 | Date recovery | ffprobe | Many file dates are copy days; embedded `creation_time` recovered 1,119 of them |
| 3 | Queue | TSV queues | Priority order; files over 60 min go last; "defer to end" beats killing jobs |
| 4 | Level | ffmpeg highpass + speechnorm + loudnorm | Keep the original alongside the leveled copy |
| 5 | Transcribe + speakers | WhisperX large-v3, pyannote, voiceprints | Mark speaker names as automatic matches |
| 6 | Deep pass | lower VAD, larger beam | A context prompt can echo into silence as fake lines: filter them; never prime with claim words |
| 7 | Keyword sweep | curated lexicon + auto terms | Filenames are the owner's own index (tags, deliberate misspellings) |
| 8 | Meaning search | nomic-embed | Catches the same idea in different words |
| 9 | Correlation | event timeline | Report artifacts honestly (TV, copy-day stamps) |
| 10 | Synthesis | local LLM summaries | "Tension" line includes the recorder's own conduct |
| 11 | Packets | Markdown + print | Tiers: family / care team (consent) / advocate (certified mail) / counsel |

**GPU safety:** gate every item on free VRAM and support a pause file, so renders and other jobs are never starved.
**Runner logs:** timestamps are item *start* times.
