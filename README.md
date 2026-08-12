# LabLens

**Live demo:** _lablens.streamlit.app_

LabLens is a web app that turns lab report values like CBC, Lipid Profile, Liver Function, Kidney
Function, Thyroid Panel, or Blood Sugar into a plain language, pattern-based health summary.
Upload a PDF, scan a report QR code, or type values in by hand.

Try it instantly with the **"Load sample data"** button on the landing screen, no upload needed.

---

## How it works

It extracts laboratory values from differently formatted report documents, normalizes them into a consistent structure, and applies transparent rule-based checks to identify notable patterns and explain them in plain language.

```
PDF (multiple laboratory layouts)
   │
   ├─ PyMuPDF text extraction
   ├─ pdfplumber (fallback)
   ├─ PyPDF2 (fallback)
   └─ Tesseract OCR (fallback, for scanned/image-only PDFs)
   │
   ▼
report-type detection (keyword scoring across 6 panel types)
   │
   ▼
alias-based value extraction (regex + line-parsing, per-parameter alias lists —
e.g. "hemoglobin"/"haemoglobin"/"hb"/"hgb" all resolve to the same field)
   │
   ▼
unit normalization + reference-range classification (sex-aware)
   │
   ▼
rule-based pattern matching (~48 hand-written clinical patterns across 6 panels)
   │
   ▼
plain-language clinical summary
```

Every value that gets extracted is shown back to the user in an explicit extraction report
(found vs. missing, per parameter) before analysis runs-the pipeline is designed to be
semi-automated and reviewable, not a black box.

**The interpretation engine uses a rule-based approach** — laboratory values are evaluated against configured reference ranges and predefined clinical patterns to generate corresponding observations and explanations. The rules are kept separate from the extraction pipeline, making the system easier to inspect and modify.

## Features

- **6 report types** — CBC, Lipid Profile, LFT, KFT, Thyroid Panel, Blood Sugar/Diabetes Profile
- **3 ways to get values in** — manual entry, PDF upload (auto-detects report type), or QR code
  (camera or uploaded image)
- **Trend tracking** — line charts across visits, per report type and parameter
- **Insights** — trajectory classification, visit-over-visit comparison, next-step suggestions,
  all derived from the same rule engine that powers the per-report results
- **Report Vault** — keep any file (X-ray, MRI, prescription, other scans) tagged and organized
  alongside analyzed reports

## Architecture

```
app.py      UI, session state, routing, rendering
engine.py   extraction (PDF/OCR/regex), classification, rule evaluation
rules.py    ~48 declarative clinical pattern rules across 6 panels
config.py   parameters, reference ranges, report-type registry
```

Data is stored in `st.session_state` and remains limited to the current browser session. No report data is written to disk or persisted across sessions.

## Tech stack

Python, Streamlit, PyMuPDF/pdfplumber/PyPDF2/Tesseract (PDF+OCR extraction), OpenCV (image processing), pandas.

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

`packages.txt` lists the system libraries (`libzbar0`, `tesseract-ocr`, `poppler-utils`) needed
for QR decoding and OCR — Streamlit Community Cloud installs these automatically from that file.

## Disclaimer

LabLens is an educational project for exploring patterns in lab report data. It is **not** a
medical device, does not provide a diagnosis, and is not a substitute for advice from a qualified
healthcare professional. Reference ranges shown are configured defaults and may differ from the
range printed on an actual lab report.
