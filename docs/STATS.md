# Aggregate stats (no PII)

| Measure | First run, 2026-09-29 | 2026-09-30 | 2026-10-01 | 2026-10-02 (morning) | 2026-10-02 (afternoon) | 2026-10-02 (evening) | 2026-10-07 |
|---|---|---|---|---|---|---|---|
| Recordings indexed | 2,047 (5 device sources) | 2,047 (5 device sources) | 2,073 | 2,073 | 2,073 (plus 37 new from two phones today, queued) | 2,073 (plus 37 new, processed) | 2,408 (2,290 catalogued + 118 new from 10/5–10/7 pulls) |
| Transcripts | 2,041 (~750 hours of audio) | 2,041 (~750 hours of audio) | 2,041 (~750 hours of audio) | 2,041 (~750 hours of audio) | 2,041 (~750 hours of audio) | 2,041 (~750 hours of audio) | 2,376 of 2,394 phone-pull recordings speaker-separated; 13 queued |
| Deep (fine-comb) pass reports | 417 | 707 | 1,808 (1,681 recordings + 127 long-file chunks) | 2,483 (2,010 recordings + 473 long-file chunks) | 2,568 (2,015 recordings + 553 long-file chunks) | 2,800 (2,031 recordings + 769 long-file chunks) | 4,150 (incl. 984 long-recording chunks) |
| Embedding files | 1,977 | 2,380 | not recounted | not recounted | not recounted | not recounted | 2,735 document vectors |
| Agency-related emails indexed | 79 | 79 | 79 | 79 | 79 | 79 | not recounted |
| Recording dates recovered from metadata | 1,119 | 1,119 | 1,119 | 1,119 | 1,119 | 1,119 | not recounted |
| Treatment-era recordings with keyword hits | 969 | 969 | 969 | 969 | 969 | 969 | not recounted |
| Deep-inspection queue | 882 queued (~427 h audio) | 159 of 882 done, running overnight on one 16 GB GPU | 877 of 882 done; long files moved to 15-minute chunks | long-file chunks: all higher-priority pieces done; 421 low-signal pieces not yet queued | 243 low-signal pieces re-queued (181 more were silent); quick first pass on a 16-hour file: 12 of 65 pieces need the deep pass | all waiting long-file pieces processed or confirmed silent; quick first pass on 79 pieces | 13 queued; GPU-host submit hang fixed with a 90 s watchdog |
| New second-device recordings (Sep 26–29) | – | 39 queued, 35 processed, 3 unreadable files logged as custody items | – | – | – | – | – |

| Silent / background-sound stretches checked against the timeline | – | – | 425 (3 near an agency contact) |

Numbers only. No names, dates of specific events, or content.
