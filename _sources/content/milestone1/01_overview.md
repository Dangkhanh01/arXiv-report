# Milestone 1 — Data Crawling Overview

## 1. Objectives & Course Context

The primary objective of Milestone 1 is to build a robust, reproducible data acquisition pipeline that harvests the raw foundation for the downstream parsing (Milestone 2) and machine learning entity matching (Milestone 3) stages.

Unlike typical web-scraping assignments that collect metadata or PDFs, our mandate requires collecting:
1. **Full-Text LaTeX Sources**: The complete `.tex` and `.bib` source files across **every single version** ($v_1, v_2, \dots, v_N$) of each assigned publication.
2. **Comprehensive Metadata**: Accurate titles, author rosters, canonical submission dates (from $v_1$), and revision histories.
3. **Structured Reference Networks**: External bibliographic references fetched via the Semantic Scholar Graph API.

---

## 2. Assigned Scope & Partitioning

The teaching team assigned four disjoint, verified ID ranges totaling **20,000 unique publications** (5,000 publications per member). The month boundaries have been empirically verified against the live repository:

| Member / Account Pool | Assigned Range (Start — End) | Total Papers | Verified Month Boundary |
|:---|:---|:---:|:---|
| **Danh** (`Danh`, `Danh1`, `Danh2`) | `2606.15734` — `2606.20733` | 5,000 | Single month (June 2026) |
| **Khánh** (`Khánh`, `Khánh1`, `Khánh2`) | `2602.19870` — `2603.00579` | 5,000 | February — March 2026 boundary verified |
| **Khang** (`Khang`, `Khang1`, `Khang2`) | `2609.02834` — `2609.07833` | 5,000 | Single month (September 2026) |
| **Nguyên** (`Nguyên`, `Nguyên1`, `Nguyên2`) | `2601.23156` — `2602.04869` | 5,000 | January — February 2026 boundary verified |

Each member operates a sequence of 3 sub-accounts (1,667 / 1,667 / 1,666 papers) backed by Google Drive synchronization to ensure fault-tolerant collection without overlapping requests.

---

## 3. Data Specification & Target Tables

In Milestone 1, no data submission to external platforms (such as Hugging Face) is required. The collected corpus is maintained in durable local/Drive storage to serve as inputs for Milestone 2. 

The two published tables specified for this milestone are:

### Table: `papers`
| Column | Type | Nullable | Description |
|:---|:---|:---:|:---|
| `arxiv_id` | String | No | Canonical identifier (e.g., `2606.15734`) |
| `title` | String | No | Full paper title |
| `authors` | List of Strings | No | Clean list of author names |
| `submission_date`| String (ISO) | No | Canonical submission timestamp of version $v_1$ (UTC) |
| `revised_dates` | List of Strings | No | Submission timestamps of revisions $v_2 \dots v_N$ |
| `venue` | String | Yes | Journal / conference venue if available |

### Table: `references`
| Column | Type | Nullable | Description |
|:---|:---|:---:|:---|
| `arxiv_id` | String | No | Citing paper arXiv ID |
| `ref_arxiv_id` | String | No | Cited paper arXiv ID (matching pool) |
| `ref_title` | String | No | Title of the cited paper |
| `ref_authors` | List of Strings | No | Author roster of the cited paper |
| `ref_submission_date` | String (ISO) | No | Canonical $v_1$ submission date of cited paper |
| `ref_s2_id` | String | No | Semantic Scholar internal paper identifier |

---

## 4. Key Constraints & Policies
- **Figure Removal by Extraction**: Figure binaries (PNG, JPG, PDF) make archives arbitrarily heavy. As mandated, figures are removed by *selective extraction*: only `.tex` and `.bib` files are extracted from tarballs. LaTeX markup lines such as `\includegraphics` and `\begin{figure}` remain intact inside the `.tex` files.
- **Empty Versions (`no_tex`)**: Versions submitted as direct PDFs without LaTeX source yield no `.tex` files. These are preserved as explicit `no_tex` records with empty directories and cryptographic receipts rather than omitted, preserving authentic version coverage.
