# arXiv Project — Jupyter Book Report Template

This repository contains the official, publication-grade **Jupyter Book** report for the **arXiv Knowledge Discovery and Entity Resolution Project** (HCMUS Intro to Data Science).

The book features an **auditable, compilation-time execution pipeline**: all figures, distributions, and performance tables are generated dynamically at build time using Plotly and pandas Styler from raw measurement data.

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

## 🔄 How to Ingest Real Data from Google Colab

When a crawling session completes on Google Colab or when the group aggregates the full 20,000-paper corpus:

1. Download the exported report artifacts:
   - `summary.json` (from `metrics.summarize_corpus`)
   - `benchmark.json` (from `metrics.summarize_benchmark`)
   - `resource_samples.csv` (periodic RAM & Disk samples)
   - `papers_unique.csv` (from `reports.aggregate_reports`)
2. Overwrite the files located in `book/data/`:
   ```text
   book/data/
   ├── summary.json
   ├── benchmark.json
   ├── resource_samples.csv
   └── papers_unique.csv
   ```
3. Re-build the book:
   ```bash
   jupyter-book build --all book/
   ```
   All notebooks will automatically re-run, recalculate KPIs, and re-render the interactive charts with your real data!

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
