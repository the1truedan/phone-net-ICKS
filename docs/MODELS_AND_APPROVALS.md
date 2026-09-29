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

## Official links
- Whisper large-v3: https://huggingface.co/openai/whisper-large-v3 · faster-whisper: https://github.com/SYSTRAN/faster-whisper · WhisperX: https://github.com/m-bain/whisperX
- wav2vec2 alignment (torchaudio): https://pytorch.org/audio/stable/generated/torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H.html
- pyannote speaker-diarization-community-1 (gated): https://huggingface.co/pyannote/speaker-diarization-community-1
- Gemma: https://ai.google.dev/gemma · nomic-embed-text-v2-moe: https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe · Ollama: https://ollama.com/
- LiteLLM: https://github.com/BerriAI/litellm · Hister: https://github.com/asciimoo/hister
- adb: https://developer.android.com/tools/adb · FFmpeg: https://ffmpeg.org/ · rclone: https://rclone.org/ · Tesseract: https://github.com/tesseract-ocr/tesseract · scrcpy: https://github.com/Genymobile/scrcpy
- Claude Code: https://docs.anthropic.com/en/docs/claude-code · Claude: https://claude.ai/ · Grok: https://grok.com/ · ChatGPT: https://chatgpt.com/
  · Codex CLI: https://github.com/openai/codex · OpenCode: https://opencode.ai/ · Pi coding agent: https://github.com/badlogic/pi-mono
