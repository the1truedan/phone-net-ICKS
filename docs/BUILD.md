# Build and run (v0.3.1, reference)

## Requirements by part
| Part | Runs on | Needs |
|---|---|---|
| Intake (adb pull, diff, SHA-256) | any Linux/Mac | USB-C cable, phone with USB debugging on, `adb`, `coreutils` |
| Custody (dates, manifests) | any | `ffprobe` (FFmpeg), Python 3 |
| Transcribe + speakers | NVIDIA GPU, 12–16 GB VRAM | CUDA driver, `nvidia-container-toolkit`, WhisperX, pyannote, Hugging Face token with the pyannote terms accepted |
| Summaries + meaning search | GPU (or fast CPU, slowly) | Ollama; `gemma` (12B class) and `nomic-embed-text-v2-moe` pulled locally |
| OCR of scans | any | Tesseract, OCRmyPDF, Poppler |
| Account exports | any | the account's own export (notes, calendar, texts), `rclone` for your own cloud drive |
| Portal records (planned) | any | official export or records request; `scrcpy` only as a last resort |

Minimum practical hardware: one 16 GB NVIDIA GPU box, 32 GB RAM, a local SSD work dir, and a separate disk for evidence.

## Run
```bash
cd stack
mkdir -p evidence work secrets && echo "<your HF token>" > secrets/hf_token.txt   # never commit
docker compose up -d ollama
docker compose exec ollama ollama pull nomic-embed-text-v2-moe
docker compose build asr tools && docker compose up -d asr tools
```
Pause the GPU queue any time: `touch stack/work/PAUSE` (remove to resume).

## Not containerized on purpose
- **Mac intake:** `adb` and `ffmpeg` via Homebrew work fine; USB passthrough into Docker on macOS is unreliable.
- **Your evidence:** stays on your own disk, mounted read-only for originals.

Ansible is not needed for one or two machines; the compose file plus this page is the whole setup.
