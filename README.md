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

Before replacing output files, the script verifies **every selected report ZIP** against its adjacent `backup_receipt.json`: run ID, archive filename, byte count and SHA-256 must match. Missing or mismatched receipts stop ingestion, including an invalid earlier checkpoint. `run_metadata.json` records the verified report inputs. This verifies report transport integrity. Adjacent corpus ZIPs, when present, are verified separately using their corpus receipt entry and CRC. Neither check establishes semantic correctness.

Historical provenance records cover 201 **report ZIPs** across 107 runs. Retained run summaries record CPU-only flags; original archives/environment are not independently reverified in this workspace. Report receipts do not establish corpus integrity, accelerator configuration or final merged output size. The aggregator now also verifies adjacent corpus ZIPs when present, but reports merged filesystem size as unmeasured until a selected merged tree is actually measured.

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

## QC and reproducibility

The versioned `config/assignments.json` is the report repository's assignment source
(including recorded month boundaries); it is independent of the code repository at
build time. Use `--assignments PATH` for a different experiment. Coverage is computed
from ID sets and nonempty title/date metadata, with missing, unexpected and
wrong-member counts recorded separately.

Ingestion rejects missing/malformed required entries, run identity mismatches,
invalid counters and selected reference-pool/count mismatches. Expected versions
are merged across checkpoints; absent versions remain explicitly missing. Reference
rows are selected from the same snapshot as their counters, never unioned across
retries. Observed citation rows come from actual stores; unknown counts stay null.

Outputs are built in a sibling staging directory and published as a directory
snapshot. Ordinary publication errors roll back to the previous snapshot. Run one
writer at a time and build the Book after ingestion; an interrupted directory swap
may leave `.data-previous` beside the target for recovery. The legacy
`scripts/sync_data.py` now delegates to this same ingestion path and requires the
member/account/Milestone1 input tree; it no longer extracts a single run or copies
partial pre-aggregated files over an existing report.

The checked-in summaries were corrected only where retained CSVs support a value.
The previous assumed +300 citation count and unverified 6.87 GiB corpus-size claim
are no longer presented as measurements. Authors/revision/reference field audits,
upstream rechecks, original CPU-only evidence and public deployment still require
the corresponding external artifacts. See [reviewQC.md](reviewQC.md).
