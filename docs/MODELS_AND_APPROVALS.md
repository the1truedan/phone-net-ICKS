# Free tools, models, approvals (outline)

## Tools (all free)
adb (Android platform-tools) · ffmpeg/ffprobe · rclone · poppler (pdftoppm) · tesseract / ocrmypdf · Python 3 ·
conda env for WhisperX · Ollama

## Models
| Use | Model | Access |
|---|---|---|
| Transcription | WhisperX large-v3 (faster-whisper) | open |
| Word alignment | wav2vec2 (WhisperX default for English) | open |
| Speaker diarization | `pyannote/speaker-diarization-community-1` | **Hugging Face gated: accept the model terms, then use an HF token** |
| Summaries | gemma4:12b via Ollama | open |
| Embeddings | nomic-embed-text-v2-moe via Ollama | open |

## Hardware used in the first run (reference only)
One 16 GB NVIDIA GPU box for transcription/diarization/summaries; a Mac for intake, extraction and search; a USB drive
for the evidence store. Nothing required cloud compute.

## AI assistants used for building (not for processing case audio)
Claude Code · Grok Build · ChatGPT/Codex. Session context came from AgentsView (session index) and Hister MCP
(shell/browser history). Case audio and transcripts were processed by the local models above.
