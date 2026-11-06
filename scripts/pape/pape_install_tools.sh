#!/usr/bin/env bash
# P.A.P.E. (Paper Accessibility, Parsing & Evidence) tool install, Mac. Re-runnable; installs only what is missing.
#   bash scripts/pape_install_tools.sh
# Scan: SANE (ScanSnap). Parse: ocrmypdf + Tesseract (+ all languages), RapidOCR (tiny ONNX OCR, CPU), llama.cpp (GGUF OCR).
# Accessibility (the tools a digital-accessibility job lists, open-source stand-ins where the named one is paid/Windows):
#   veraPDF (PDF/UA check), pa11y + axe-core CLI (WAVE / axe DevTools stand-ins), python-docx / python-pptx (Word /
#   PowerPoint checks), pikepdf + pypdf (PDF structure). Screen reader on the Mac = VoiceOver (built in).
set -uo pipefail
ok(){ printf '  ✅ %s\n' "$*"; }
echo "== Homebrew"
for f in sane-backends ocrmypdf tesseract tesseract-lang unpaper jbig2enc pngquant ghostscript poppler qpdf img2pdf llama.cpp verapdf pandoc; do
  brew list --versions "$f" >/dev/null 2>&1 && ok "$f" || { brew install "$f" >/dev/null 2>&1 && ok "$f (installed)" || echo "  ❌ $f"; }
done
echo "== Python tools venv (~/models/pape_tools/.venv)"
UV=$(command -v uv || echo ~/.local/bin/uv)
mkdir -p ~/models/pape_tools && cd ~/models/pape_tools || exit 1
[ -x .venv/bin/python ] || "$UV" venv -q -p 3.12 .venv
VIRTUAL_ENV=$PWD/.venv "$UV" pip install -q rapidocr onnxruntime python-docx python-pptx pypdf pikepdf pillow pdfplumber \
  && ok "rapidocr onnxruntime python-docx python-pptx pypdf pikepdf pillow pdfplumber" || echo "  ❌ python tools"
echo "== Node CLIs (~/models/pape_tools/node)"
mkdir -p node && cd node && [ -f package.json ] || npm init -y >/dev/null
npm install --silent pa11y @axe-core/cli >/dev/null 2>&1 && ok "pa11y @axe-core/cli" || echo "  ❌ node CLIs"
echo "== Versions"
tesseract --version 2>&1 | head -1; ocrmypdf --version; verapdf --version 2>&1 | head -1; llama-mtmd-cli --version 2>&1 | grep -m1 version
~/models/pape_tools/.venv/bin/python -c "import rapidocr,docx,pptx,pikepdf;print('rapidocr', rapidocr.__version__ if hasattr(rapidocr,'__version__') else 'ok', '· docx · pptx · pikepdf', pikepdf.__version__)"
npx --prefix ~/models/pape_tools/node pa11y --version 2>/dev/null | sed 's/^/pa11y /'; npx --prefix ~/models/pape_tools/node axe --version 2>/dev/null | sed 's/^/axe /'
