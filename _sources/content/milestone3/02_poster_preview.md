# Final Dataset & Poster Presentation

This section outlines the culminating deliverables for the project, including the public dataset distribution schema on Hugging Face and the academic poster session requirements.

---

## 1. Public Release: Hugging Face Parquet Dataset

At the conclusion of Milestone 3, all processed data from the three milestones will be hosted publicly as a **Hugging Face Dataset** in sharded Parquet format, allowing high-performance streaming without custom loading scripts.

### Dataset Table Registry (6 Unified Tables)

| Table | Originating Milestone | Schema & Content Summary |
|:---|:---:|:---|
| **`papers`** | Milestone 1 | Assigned publications, canonical $v_1$ submission date, revised dates, authors, title |
| **`references`** | Milestone 1 | Citing-cited paper relationships holding arXiv-keyed references and S2 IDs |
| **`elements`** | Milestone 2 | Distinct parsed document elements deduplicated across version histories |
| **`hierarchy`** | Milestone 2 | Node-parent directed edges for all version document trees |
| **`bibtex`** | Milestone 2 | Clean, deduplicated BibTeX entries with unionized fields |
| **`predictions`** | Milestone 3 | Reference matching rankings with top-5 candidate predictions and MRR scores |

```text
Hugging Face Repository Layout:
└── <dataset-repo>/
    ├── README.md (Dataset Card with YAML configs)
    └── data/
        ├── papers/*.parquet
        ├── references/*.parquet
        ├── elements/*.parquet
        ├── hierarchy/*.parquet
        ├── bibtex/*.parquet
        └── predictions/*.parquet
```

---

## 2. Poster Presentation (Portrait A2)

The final evaluation for the course culminates in a live **Poster Session**:
- **Format**: Single-page poster in **Portrait A2** form factor submitted as a `.pptx` file.
- **Key Highlights**:
  - The distinctive architecture and efficiency of the scraping and parsing engines.
  - Feature importance analysis and ablation studies of the matching models.
  - Overall pipeline statistics, MRR@5 achievements, and entity resolution findings.
