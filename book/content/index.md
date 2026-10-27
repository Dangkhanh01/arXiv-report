# arXiv Knowledge Discovery & Entity Resolution

Welcome to the comprehensive technical report for the **arXiv Knowledge Discovery and Entity Resolution Project**, conducted as part of the *Introduction to Data Science* course at VNUHCM - University of Science (HCMUS).

> [!NOTE]
> **Milestone 1 Submission Scope (20,000 Papers)**: This report compiles and evaluates the complete, auditable crawl measurements harvested across all 20,000 assigned arXiv papers on Google Colab CPU (`Linux x86_64; Python 3.13 / 3.14`). All KPI tables, percentile breakdowns, and resource consumption timelines are generated dynamically at build time from raw experimental data aggregated across all 4 team members (Danh, Khang, Khánh, Nguyên).

---

## 1. Project Overview & Research Context

Scientific literature published on [arXiv.org](https://arxiv.org) forms one of the largest open-access scholarly corpuses in the world, containing over two million papers. While traditional data engineering workflows primarily focus on bibliographic metadata or compiled PDF documents, this project pioneers an end-to-end data science pipeline that mines **full-text LaTeX source files** and constructs a unified entity resolution graph.

The project is structured into three cumulative milestones:

```text
+-----------------------------------------------------------------------------------+
|                            End-to-End Project Pipeline                            |
+-----------------------------------------------------------------------------------+
                                          |
  [Milestone 1: Data Crawling]            v
  +-------------------------------------------------------------------------------+
  | - Targeted Discovery: OAI-PMH `arXivRaw` (20,000 assigned papers, v1..vN)    |
  | - Full-Text Sources: Clean extraction of `.tex` & `.bib` (figure removal)     |
  | - Reference Extraction: Semantic Scholar API (all rows + arXiv pool)          |
  | - Scalable System: Rate limiting (3.1s), cache, Colab CPU benchmarking        |
  +-------------------------------------------------------------------------------+
                                          |
  [Milestone 2: Hierarchical Parsing]     v
  +-------------------------------------------------------------------------------+
  | - Multi-file Gathering: Transitive `\input` & `\include` compilation path     |
  | - Hierarchy Construction: Document -> Section -> Subsection -> Sentence/Math   |
  | - LaTeX Standardization: Math normalization (`$` and `\begin{equation}`)      |
  | - Cross-Version Deduplication: Full-text elements & unified BibTeX entries    |
  +-------------------------------------------------------------------------------+
                                          |
  [Milestone 3: Entity Resolution]        v
  +-------------------------------------------------------------------------------+
  | - Reference Matching: Link BibTeX entries to external arXiv reference IDs    |
  | - Machine Learning: Feature engineering, text matching, evaluation at MRR@5   |
  | - Public Release: 6 sharded Parquet tables on Hugging Face & A2 Poster       |
  +-------------------------------------------------------------------------------+
```

---

## 2. Project Team & Responsibilities

Our team consists of 4 members collaborating under strict engineering contracts and reproducible workflows:

| Member | Primary Responsibilities | Assigned Partition | Verified Corpus |
|:---|:---|:---:|:---:|
| **Khánh** | Discovery, Metadata & Version History (`oai-pmh/arXivRaw`, date resolution) | 5,000 papers | 5,000 papers (100%) |
| **Khang** | Full-Text Source Extraction (`.tex`/`.bib` whitelist, figure removal) | 5,000 papers | 5,000 papers (100%) |
| **Nguyên** | Reference Mining & Ingestion (Semantic Scholar Graph API pagination) | 5,000 papers | 5,000 papers (100%) |
| **Danh** | Pipeline Orchestration & Reporting (resource telemetry, Jupyter Book synthesis) | 5,000 papers | 5,000 papers (100%) |

---

## 3. Structure of this Report

This **Jupyter Book** serves as the cumulative, auditable report for the project. For the **Milestone 1 submission**, the report focuses exclusively on the complete data acquisition, source cleaning, and resource benchmarking pipeline. Milestone 2 will be incorporated sequentially into this book in future milestones, and Milestone 3 will be accompanied by an A2 poster:

1. **[Milestone 1 — Data Crawling](milestone1/01_overview.md)**:
   - Problem statement and assigned scope (20,000 papers across 4 member partitions).
   - Technical methodology (OAI-PMH `arXivRaw`, mirror streaming, Semantic Scholar pagination, dual-backup, and pacing policies).
   - [Corpus Statistics](milestone1/03_corpus_stats.ipynb): Key performance indicators, storage reduction percentiles (95.74% saved), version multiplicity distributions, and citation pool categorization.
   - [Performance Benchmarking](milestone1/04_performance.ipynb): CPU, RAM (RSS), and Disk footprints synthesized across 107 Google Colab CPU-only runs, including per-paper processing time distributions.
2. **[Academic References](references.md)**: Complete bibliographic references complying with scholarly standards.

