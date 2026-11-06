# P.A.P.E. · Paper Accessibility, Parsing & Evidence

The paper side of phone-net · I.C.K.S. Notices, care plans, receipts and handbooks go through a document feeder scanner and come
out as searchable PDFs that screen readers can use, with the same custody files as a phone pull. Everything runs on the
family's own computer. Nothing is uploaded.

## Install (Mac)

```
bash scripts/pape/pape_install_tools.sh     # SANE, ocrmypdf + Tesseract, veraPDF, pikepdf, RapidOCR, pa11y/axe; only what is missing
```

The Python tools live in `~/models/pape_tools/.venv`. Output goes to `$PAPE_OUT` (default `~/pape_scans`).

## The scripts

| Step | Script | What it does |
|---|---|---|
| Scan | `pape_scan.sh` | Feeder scan, both sides, to a searchable PDF. Writes `SHA256SUMS.txt`, `custody_log.txt` and `PULL_LOG.txt`, like a phone pull. |
| Route | `pape_route.py` | Per page, picks the cheapest reader that is good enough (text layer, Tesseract, RapidOCR, a vision model for tables). |
| Tag | `pape_tag_pdf.py` | Searchable PDF to a tagged PDF with title, language and reading order (PDF/UA-1 target, checked with veraPDF). |
| Process | `pape_process.py` | The full treatment for a file or folder: tag, audit, plain-language brief (with the optional A.I.D.A. agents). |
| Audit | `pape_a11y_audit.py` | Every PDF in a folder: PDF/UA-1, structure, contrast, which source it came from. |
| Audit a site | `pape_web_audit.py` | A public website and the PDFs it links to, against WCAG 2.1 AA (pa11y + axe). |
| Audit a list | `pape_pdf_url_audit.py` | A list of public PDF links, each cited by its source. |
| Links | `pape_link_check.py` | Every link on a set of pages: status, final address, login walls, soft 404s. |
| Changes | `pape_version_diff.py` | What changed between two versions of an official document, and what kind of change it is. |
| Letters | `pape_md_to_pdf.py` | Markdown to a tagged PDF that passes PDF/UA-1, for letters and applications. |

## Tools it stands on

All free and open source, all run on the family's computer.

| Job | Tool | Link |
|---|---|---|
| Scanner driver (Fujitsu ScanSnap and many more) | SANE `scanimage` | http://www.sane-project.org/ |
| Searchable PDF from a scan | OCRmyPDF | https://github.com/ocrmypdf/OCRmyPDF |
| Text recognition, 160+ languages | Tesseract + tessdata | https://github.com/tesseract-ocr/tesseract · https://github.com/tesseract-ocr/tessdata |
| Second opinion OCR (small, CPU) | RapidOCR on ONNX Runtime | https://github.com/RapidAI/RapidOCR · https://onnxruntime.ai/ |
| Tables and hard pages (vision model) | PaddleOCR-VL GGUF via llama.cpp `llama-mtmd-cli` | https://github.com/PaddlePaddle/PaddleOCR · https://github.com/ggml-org/llama.cpp |
| Page cleanup | unpaper, img2pdf, jbig2enc, pngquant | https://github.com/unpaper/unpaper · https://gitlab.mister-muffin.de/josch/img2pdf · https://github.com/agl/jbig2enc · https://pngquant.org/ |
| PDF structure | pikepdf, pypdf, qpdf, Poppler (`pdftotext`, `pdffonts`, `pdfimages`), pdfplumber, Ghostscript | https://github.com/pikepdf/pikepdf · https://github.com/py-pdf/pypdf · https://github.com/qpdf/qpdf · https://poppler.freedesktop.org/ · https://github.com/jsvine/pdfplumber · https://www.ghostscript.com/ |
| PDF/UA-1 check | veraPDF | https://verapdf.org/ |
| Tagged PDF print | Chromium `--export-tagged-pdf` (Brave on the Mac) | https://www.chromium.org/ · https://brave.com/ |
| Website accessibility (WCAG 2.1 AA) | pa11y (HTML_CodeSniffer) + axe-core CLI | https://pa11y.org/ · https://github.com/dequelabs/axe-core-npm |
| Word and PowerPoint checks | python-docx, python-pptx | https://github.com/python-openxml/python-docx · https://github.com/scanny/python-pptx |
| Images | Pillow | https://python-pillow.org/ |
| Plain-language change notes | a local model through Ollama (default `gemma4:12b`) | https://ollama.com/ |
| Markdown to letters | pandoc | https://pandoc.org/ |
| Optional: triage and plain-language briefs | ada-doc-check, A.I.D.A. lab | https://github.com/the1truedan/ada-doc-check · https://github.com/the1truedan/aida-complex-doc-lab |
| Screen reader check | VoiceOver (built into macOS) | https://www.apple.com/accessibility/vision/ |

Standards it checks against: PDF/UA-1 (ISO 14289-1, https://pdfa.org/resource/iso-14289-pdfua/) and WCAG 2.1 AA (https://www.w3.org/TR/WCAG21/).

## How it came about

From the coding-agent session records (AgentsView session IDs only; no message text from the care record). Times are Central.

| When | What happened |
|---|---|
| Oct 26, 2026 | A used Fujitsu ScanSnap S1500M bought on ShopGoodwill, Buy Now, **$14.99** (session `18860528`). |
| Oct 29, 3:31 PM | Shipped by FedEx. |
| Nov 1, 10:40:57 AM | Arrived. First words to the agent: *"ALL YOUR PAPES ARE BELONG TO US … there is no paper? paper trail? paper parade? THE PAPE"* (session `6d0b256a`). |
| 10:41:26 | The free scanner driver (SANE) starts installing; the release is earmarked in TODO.md. |
| 10:42:43 | *"chute open, plugged direct to mac."* |
| 10:42:55 | The Mac sees the scanner on USB. |
| 10:43:03 | Driver test answers "feeder out of documents": the driver works, no Fujitsu software needed. |
| 10:43:34 | Tools check: OCRmyPDF, Tesseract with 163 languages, feeder in duplex mode. |
| 10:43:58 | `pape_scan.sh` committed. |
| 10:44:12 | *"paper in, ready for test."* |
| **10:45:16** | **First automated scan: 6 pages, about 1,400 words, 53 seconds, with checksums and a custody log.** |
| 10:50:36 | Blank backs set aside before text recognition. |
| 11:56 AM – 2:17 PM | OCR bake-off, Mac installer, website audit, per-page router (P.A.P.E.R.). |
| 3:52 PM | Resource ledger: broken links kept with the date they broke and where the content moved. |
| 9:09 PM | Link checker and markdown to PDF/UA-1. |
| Nov 5, 11:23 PM | Public as v0.9.0 PAPER TRAIL. |

**Arrival to first automated scan: 4 min 19 s. Plugged in to a searchable PDF: 2 min 33 s.** The name was there from the
first message: "paper trail?"

## Your own sources

The audit names a few public government sources by itself. To name the agencies and providers in your own case, put them in
`~/.config/pape/agencies.json` (`{"Name": "regex"}`). That file stays on your computer.

## Rules

- A person signs off. The tools prepare; nothing is sent anywhere by itself.
- Broken links are kept, with the date they broke and where the content moved, never deleted.
- Fixed copies keep the original words (the audit reports the share kept).
