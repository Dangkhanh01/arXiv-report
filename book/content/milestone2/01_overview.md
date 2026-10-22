# Milestone 2 — Parsing & Standardization Overview

> [!NOTE]
> **Forward Compatibility Architecture**: This section establishes the structural framework for **Project Milestone 2 — Hierarchical Parsing and Standardization**, based on the course statement in the [HCMUS Course Specifications](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/). Detailed empirical results, execution statistics, and parsed hierarchy distributions will be integrated here upon Milestone 2 execution.

---

## 1. Objectives

Milestone 2 transitions the project from unstructured data harvesting to structured document representation and linguistic standardization. Consuming the clean `.tex` and `.bib` files produced in Milestone 1, the pipeline transforms raw LaTeX code into an auditable hierarchical tree and deduplicates content across document revisions.

The downstream reference matching pipeline in Milestone 3 relies directly on the clean elements and unified BibTeX tables produced in this stage.

---

## 2. Core Components of the Processing Pipeline

```{mermaid}
graph TD
    A[Raw .tex Sources v1..vN] --> B[Multi-File Gathering: Compilation Path]
    B --> C[LaTeX Hierarchy Parser]
    C --> D[Leaf Extraction: Sentences, Block Formulas, Figures]
    D --> E[Standardization & Normalization]
    E --> F[Cross-Version Deduplication]
    F --> G1[Table: elements]
    F --> G2[Table: hierarchy]
    F --> G3[Table: bibtex]
```

1. **Multi-File Gathering**: Detect the primary publication root (the file declaring `\documentclass`) and follow `\input` and `\include` directives transitively, ignoring commented inclusions.
2. **Hierarchy Construction**: Map structural levels (Document $\rightarrow$ Sections $\rightarrow$ Subsections $\rightarrow$ Paragraphs) down to leaf nodes (Sentences, Block Formulas, and Tables/Figures).
3. **Standardization**:
   - Math normalization: unify inline math to `$...$` and block math to `\begin{equation}...\end{equation}`.
   - LaTeX cleanup: eliminate purely visual styling commands (e.g., `\centering`, `\midrule`, `[htpb]`).
4. **Deduplication Across Versions**:
   - **Full-Text Elements**: Shared sentences across revisions map to a single `element_id`.
   - **Unified BibTeX Entries**: Unionize fields (author, title, year, doi) across duplicate `\bibitem` entries and rename `\cite{}` commands accordingly.

---

## 3. Published Target Tables

Milestone 2 defines three primary dataset tables that feed directly into the final Hugging Face release:

| Table | Columns (types) | Description |
|:---|:---|:---|
| **`elements`** | `element_id` (str), `arxiv_id` (str), `kind` (str), `content` (str) | Distinct deduplicated elements across all versions |
| **`hierarchy`** | `arxiv_id` (str), `version` (int), `element_id` (str), `parent_id` (str) | Directed node-parent edges per version tree |
| **`bibtex`** | `arxiv_id` (str), `citation_key` (str), `entry_type` (str), `title` (str), `authors` (list), `year` (int), `doi` (str), `journal` (str), `url` (str) | Unified, deduplicated BibTeX entries |
