# arXiv Project — Jupyter Book Report Template

This repository contains the Jupyter Book technical report for the **arXiv Knowledge Discovery and Entity Resolution Project** (HCMUS Introduction to Data Science).

All figures, distributions, and performance tables in this report are generated dynamically at build time using Plotly and pandas from the aggregated measurement data in `book/data/`.

---

## 📖 Architecture & Table of Contents

The book is organized into 4 logical Parts across all milestones:

1. **Homepage (`content/index.md`)**: Research context, 3-milestone pipeline diagram, and team responsibilities.
2. **Milestone 1 — Data Crawling**:
   - `01_overview.md`: Assigned scope (20,000 papers), target tables (`papers`, `references`).
   - `02_methodology.md`: OAI-PMH `arXivRaw`, selective `.tex`/`.bib` extraction, Semantic Scholar pagination, dual-backup.
   - `03_corpus_stats.ipynb`: **Dynamic notebook** computing success rates, size reduction bar charts, and reference distributions.
   - `04_performance.ipynb`: **Dynamic notebook** reporting wall clock time, RAM/Disk timelines, and Google Colab CPU footprints.
3. **Milestone 2 — Hierarchical Parsing & Standardization**:
   - `01_overview.md`, `02_parsing.md`, `03_standardization.md`, `04_m2_stats.ipynb`: Architecture ready for LaTeX AST trees, math normalization, and cross-version deduplication.
4. **Milestone 3 — Reference Matching & Final Delivery**:
   - `01_overview.md`, `02_poster_preview.md`: Machine learning matching pipeline, MRR@5 ranking, Hugging Face Parquet dataset, and A2 poster session.
5. **Appendix & Academic References (`content/references.md`, `references.bib`)**:
   - 26 complete scholarly citations.

---

## 🚀 Quickstart: Local Setup & Build

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
```bash
# Optional: create a virtual environment
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Build the Book Locally
Execute the Jupyter Book compiler:
```bash
jupyter-book build book/
```
The compiled HTML site will be generated inside `book/_build/html/`.

### 4. Preview the Site
Open the main page in your default browser:
- **Windows (PowerShell)**:
  ```powershell
  Start-Process "book/_build/html/index.html"
  ```
- **macOS / Linux**:
  ```bash
  open book/_build/html/index.html
  ```

---

## 🔄 Automated Data Ingestion & Aggregation

We provide an automated aggregation script [`scripts/aggregate_data.py`](scripts/aggregate_data.py) that discovers, verifies report archives against backup receipts, aggregates across all 4 team members and multiple accounts/checkpoints, and formats metrics from `input/` into `book/data/`:

Before replacing output files, the script verifies **every selected report ZIP** against its adjacent `backup_receipt.json`: run ID, archive filename, byte count and SHA-256 must match. Missing or mismatched receipts stop ingestion, including an invalid earlier checkpoint. `run_metadata.json` records the verified report inputs. This verifies report transport integrity; it does not verify source corpus ZIPs or establish semantic correctness of their contents.

The checked-in measurements predate this verification change. Their original input trees are not included here, so adding the check does not retroactively certify those archives. Re-run aggregation against the original member/account trees to obtain receipt-verified provenance. Missing historical accelerator/cache flags remain unknown rather than being filled with CPU-only/cold defaults.

### 1. Ingest & Aggregate Multi-Member Corpus (20,000 Papers)
```bash
# Auto-detect input directory from workspace
python scripts/aggregate_data.py

# Or specify custom source and target paths:
python scripts/aggregate_data.py --source /path/to/input --target book/data

# Aggregate and immediately rebuild the book:
python scripts/aggregate_data.py --build
```

### 2. Standardized Aggregated Datasets in `book/data/`
The script generates the measurement files:
```text
book/data/
├── summary.json           # Crawl KPI rates, version counts, reference totals, denominators
├── benchmark.json         # Multi-run synthesis: 107 runs, median/total wall time, peak RAM
├── resource_samples.csv   # Thinned RAM/Disk timeline samples across runs
├── papers_unique.csv      # 20,000 deduplicated papers (member, account, arxiv_id, title)
├── papers_detail.csv      # Per-paper elapsed time, version status, reference status
├── versions.csv           # 27,608 unique version records (status, before/after bytes)
└── run_metadata.json      # Provenance metadata across all 107 processed runs
```

Aggregation also writes `references_agg.csv`; this large file is excluded from Git. The Book uses per-paper citation counters for reference totals and distributions. Historical field-level reference completeness is not established by the checked-in files.

### 3. Rebuild the Book
```bash
jupyter-book build --all book/
```
All notebooks dynamically re-calculate KPIs and re-render interactive Plotly figures at build time!

Receipt-ingestion regression tests (stdlib only):

```bash
python -m unittest discover -s tests -v
```

---

## 🌐 Automated GitHub Pages Deployment

The repository includes a GitHub Actions workflow in `.github/workflows/deploy.yml`.

### One-Time Setup on GitHub:
1. Push this repository to GitHub (e.g. `https://github.com/<your-username>/arxiv-report`).
2. Go to repository **Settings** → **Pages**.
3. Under **Build and deployment**:
   - Source: Select **Deploy from a branch**.
   - Branch: Select **`gh-pages`** and folder **`/ (root)`**.
   - Click **Save**.
4. Every future commit pushed to `main` (or `master`) will automatically build the book and publish the updated report to your live GitHub Pages URL!
