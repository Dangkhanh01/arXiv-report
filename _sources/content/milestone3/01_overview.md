# Milestone 3 — Reference Matching Pipeline Overview

> [!NOTE]
> **Forward Compatibility Architecture**: This section establishes the structural framework for **Project Milestone 3 — Reference Matching Pipeline**, based on the course statement in the [HCMUS Course Specifications](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/).

---

## 1. Objectives & Real-World Machine Learning Context

Milestone 3 applies machine learning techniques to a real-world entity resolution challenge: linking extracted bibliographic citations from raw text (`bibtex` table from Milestone 2) with their true external metadata (`references` table from Milestone 1).

The problem mimics industrial entity resolution workflows where unstructured bibliographic strings (often containing OCR noise, author misspellings, or missing publication years) must be matched against large reference databases.

---

## 2. Machine Learning Pipeline Architecture

```{mermaid}
graph LR
    A[Extracted BibTeX Entries] --> B[Data Preprocessing & Normalization]
    C[Crawled Reference Metadata] --> B
    B --> D[Candidate Retrieval & Blocking]
    D --> E[Feature Engineering: Lexical, Semantic, Year Distances]
    E --> F[Ranking Model: Top-5 Predictions]
    F --> G[Evaluation: MRR@5]
```

### 1. Data Cleaning & Tokenization
Text preprocessing is applied to titles and author rosters, including lowercasing, stop-word elimination, accent stripping, and n-gram tokenization.

### 2. Ground-Truth Data Labeling
- **Manual Pool**: At least 5 assigned publications, each having at least 20 labeled BibTeX entries (minimum 100 labeled pairs total).
- **Automated Pool**: At least 10% of remaining publications with all BibTeX entries labeled using verified deterministic heuristics.
- **Data Splitting**: Partitioned at the publication level into Training, Validation, and Test sets.

### 3. Feature Engineering & Modeling
- Similarity metrics: Jaccard similarity, Levenshtein distance, TF-IDF cosine similarity, BM25 scores, and absolute publication year delta.
- Ranking algorithm: Supervised ranking classifier generating ordered top-5 candidate matches ($cand_1 \dots cand_5$).

### 4. Primary Evaluation Metric: MRR@5
The pipeline performance is formally scored using **Mean Reciprocal Rank @ 5**:

$$\text{MRR@5} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

Where $\text{rank}_i$ is the 1-indexed position of the true reference within the model's top 5 predictions, or 0 if the ground-truth reference does not appear within the top 5 candidates.
