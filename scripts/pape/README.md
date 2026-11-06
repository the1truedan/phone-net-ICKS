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

## Your own sources

The audit names a few public government sources by itself. To name the agencies and providers in your own case, put them in
`~/.config/pape/agencies.json` (`{"Name": "regex"}`). That file stays on your computer.

## Rules

- A person signs off. The tools prepare; nothing is sent anywhere by itself.
- Broken links are kept, with the date they broke and where the content moved, never deleted.
- Fixed copies keep the original words (the audit reports the share kept).
