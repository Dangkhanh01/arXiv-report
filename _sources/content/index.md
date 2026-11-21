# arXiv Knowledge Discovery & Entity Resolution

Welcome to the comprehensive technical report for the **arXiv Knowledge Discovery and Entity Resolution Project**, conducted as part of the *Introduction to Data Science* course at VNUHCM - University of Science (HCMUS).

> [!NOTE]
> Milestone 2 tracked **27,608 versions** of the **20,000 assigned publications**. Of the **18,902 publications** that qualified for handoff, **17,890 contributed parsed elements** and **1,012 had only confirmed no-TeX versions**.

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

Each member's M1 partition contained 5,000 publications, and all 5,000 IDs in each partition resolved to metadata. In M2, the four members contributed different stages of the shared parser.

| Member | Milestone 1 | Milestone 2 |
|---|---|---|
| **Khánh** | Discovery, metadata and version history through OAI-PMH | Input verification, compilation roots, include traversal and version coverage |
| **Khang** | Full-text source extraction and figure removal | Document hierarchy, sentence splitting and boundary protection |
| **Nguyên** | Reference collection through the Semantic Scholar Graph API | Bibliography extraction, field merging and citation-key unification |
| **Danh** | Crawler orchestration, resource monitoring and Jupyter Book reporting | Text and math normalization, cross-version element deduplication, pipeline integration and benchmarking |

---

## 3. Structure of this Report

This Jupyter Book covers data acquisition in Milestone 1 and the preparation of structured publications for reference matching in Milestone 2.

1. **[Milestone 1 — Data Crawling](milestone1/01_overview.md)**:
   - Problem statement and assigned scope (20,000 papers across 4 member partitions).
   - Technical methodology (OAI-PMH `arXivRaw`, mirror streaming, Semantic Scholar pagination, dual-backup, and pacing policies).
   - [Corpus Statistics](milestone1/03_corpus_stats.ipynb): Key performance indicators, storage reduction percentiles (95.74% saved), version multiplicity distributions, and citation pool categorization.
   - [Performance Benchmarking](milestone1/04_performance.ipynb): Wall time, RAM (RSS), and disk measurements across 107 recorded runs, including per-paper processing time distributions.
2. **Milestone 2 — Hierarchical Parsing and Standardization** follows a two-version publication through the parser, then evaluates coverage, deduplication and resource use across twelve runs. [Overview](milestone2/01_overview.md) · [Results and publication lookup](milestone2/04_m2_stats.ipynb)
3. **[Academic References](references.md)**

