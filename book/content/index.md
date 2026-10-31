# arXiv Knowledge Discovery & Entity Resolution

Welcome to the comprehensive technical report for the **arXiv Knowledge Discovery and Entity Resolution Project**, conducted as part of the *Introduction to Data Science* course at VNUHCM - University of Science (HCMUS).

> [!NOTE]
> **Milestone 1 Submission Scope (20,000 Papers)**: This report summarizes retained crawl measurements for 20,000 assigned arXiv IDs. Runtime strings identify Google Colab; CPU-only settings and original archive receipts are not established for all historical runs. All KPI tables, percentile breakdowns, and resource consumption timelines are generated dynamically at build time from raw experimental data aggregated across all 4 team members (Danh, Khang, Khánh, Nguyên).

---

## 1. Project Overview & Research Context

Scientific literature published on [arXiv.org](https://arxiv.org) forms one of the largest open-access scholarly corpuses in the world, containing over two million papers. While typical scholarly workflows primarily inspect bibliographic metadata or compiled PDF documents, this project builds an end-to-end data processing pipeline that collects versioned **full-text LaTeX source files** (`.tex`/`.bib`) and reference networks for assigned papers, preparing them for hierarchical parsing and entity resolution.

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

Our team consists of 4 members operating a shared crawler architecture across four non-overlapping ID partitions with synchronized aggregation:

| Member | Primary Responsibilities | Assigned Partition | Metadata-resolved IDs |
|:---|:---|:---:|:---:|
| **Khánh** | Discovery, Metadata & Version History (`oai-pmh/arXivRaw`, date resolution) | 5,000 papers | 5,000 papers (100%) |
| **Khang** | Full-Text Source Extraction (`.tex`/`.bib` whitelist, figure removal) | 5,000 papers | 5,000 papers (100%) |
| **Nguyên** | Reference Mining & Ingestion (Semantic Scholar Graph API pagination) | 5,000 papers | 5,000 papers (100%) |
| **Danh** | Pipeline Orchestration & Reporting (resource telemetry, Jupyter Book synthesis) | 5,000 papers | 5,000 papers (100%) |

---

## 3. Structure of this Report

This **Jupyter Book** serves as the cumulative, auditable report for the project. For the **Milestone 1 submission**, the report covers data acquisition, source filtering, remaining failures, and resource measurements. Milestone 2 will be incorporated sequentially into this book in future milestones, and Milestone 3 will be accompanied by an A2 poster:

1. **[Milestone 1 — Data Crawling](milestone1/01_overview.md)**:
   - Problem statement and assigned scope (20,000 papers across 4 member partitions).
   - Technical methodology (OAI-PMH `arXivRaw`, mirror streaming, Semantic Scholar pagination, dual-backup, and pacing policies).
   - [Corpus Statistics](milestone1/03_corpus_stats.ipynb): Key performance indicators, storage reduction percentiles (95.74% saved), version multiplicity distributions, and citation pool categorization.
   - [Performance Benchmarking](milestone1/04_performance.ipynb): Wall time, RAM (RSS), and disk measurements across 107 recorded runs, including per-paper processing time distributions.
2. **[Academic References](references.md)**: Complete bibliographic references complying with scholarly standards.

