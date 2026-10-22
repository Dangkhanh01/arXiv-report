# arXiv Knowledge Discovery & Entity Resolution

Welcome to the comprehensive technical report for the **arXiv Knowledge Discovery and Entity Resolution Project**, conducted as part of the *Introduction to Data Science* course at VNUHCM - University of Science (HCMUS).

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

| Member | Primary Responsibilities | Core Deliverables |
|:---|:---|:---|
| **Khánh** | Discovery, Metadata & Version History | OAI-PMH `GetRecord` client (`arXivRaw`), submission date resolution, metadata cache |
| **Khang** | Full-Text Source Extraction | Versioned source downloader, byte-exact `.tex`/`.bib` whitelist, figure removal |
| **Nguyên** | Reference Mining & Ingestion | Semantic Scholar Graph API pagination, `references_all` and `references` stores |
| **Danh** | Pipeline Orchestration & Reporting | Pipeline coordination, resource benchmarking (`psutil`), Jupyter Book synthesis |

---

## 3. Structure of this Report

This **Jupyter Book** serves as the cumulative, auditable report for the project. In strict accordance with course specifications, **all figures and tables are dynamically generated at build time** from reproducible raw measurements rather than static screenshots:

1. **[Milestone 1 — Data Crawling](milestone1/01_overview.md)**:
   - Problem statement and assigned scope (20,000 papers).
   - Technical methodology (OAI-PMH `arXivRaw`, mirror streaming, Semantic Scholar pagination, dual-backup).
   - [Corpus Statistics](milestone1/03_corpus_stats.ipynb): Interactive key metrics, size reduction distributions, and reference completeness.
   - [Performance Benchmarking](milestone1/04_performance.ipynb): CPU, RAM, and Disk footprints observed on Google Colab CPU-only runtimes.
2. **[Milestone 2 — Hierarchical Parsing & Standardization](milestone2/01_overview.md)**:
   - Specifications for LaTeX hierarchy parsing, AST tree construction, math normalization, and cross-version deduplication.
3. **[Milestone 3 — Reference Matching & Delivery](milestone3/01_overview.md)**:
   - Preview of the machine learning matching pipeline, MRR@5 ranking, Hugging Face Parquet dataset, and A2 poster presentation.
4. **[Academic References](references.md)**: Complete bibliographic references complying with scholarly standards.
