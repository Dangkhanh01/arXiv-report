# Hierarchical LaTeX Parsing Logic

> [!NOTE]
> Detailed algorithmic implementation, AST grammar definitions, and parsing success logs will be documented here during Milestone 2.

---

## 1. Multi-File Compilation Path Detection

LaTeX publications frequently partition source code across multiple `.tex` files. To reproduce the exact document rendered in the final PDF without ingesting dead or redundant code:

1. **Root File Discovery**: The root publication file is unambiguously identified by the presence of the `\documentclass` declaration.
2. **Transitive Traversal**: The parser recursively follows inclusion commands:
   - `\input{filename}`
   - `\include{filename}`
3. **Comment Filtering**: Any inclusion commands preceded by `%` (comments) are treated as plain text and ignored.
4. **Pruning Unused Files**: Auxiliary files present in the source folder that are unreachable from the root file are pruned from the compilation path.

---

## 2. Tree Hierarchy & Element Granularity

The parser transforms the document into an $N$-ary tree structure with the following levels:

```text
Document (Root)
├── Section 1
│   ├── Subsection 1.1
│   │   ├── Paragraph 1.1.1
│   │   │   ├── Leaf: Sentence 1 ("We study the entity matching problem.")
│   │   │   ├── Leaf: Inline / Block Equation
│   │   │   └── Leaf: Sentence 2
│   └── Subsection 1.2
└── Section 2 (Appendices / Acknowledgements)
```

### Parsing Rules & Leaf Specifications:
- **Sentence Splitting Integrity**: Leaf sentences represent genuine prose. The splitter does **not** split sentences on dots occurring inside:
  - Mathematical formulas (inline or block)
  - LaTeX commands (e.g., `\ref{sec.1}`)
  - Common academic abbreviations (e.g., *i.e.*, *e.g.*, *et al.*, *Fig. 1*)
  - URLs and decimal numbers (e.g., `3.14`)
- **Block Formulas**: Formatted equations inside `equation`, `align`, or `$$...$$` form distinct leaf nodes.
- **Figures & Tables**: Table environments (`table`, `tabular`) and figures (`figure`) are recognized as discrete leaf entities.
- **Inclusions**: Unnumbered sections like `\section*{Acknowledgements}` and `\section*{Appendix}` are strictly parsed.
- **Exclusions**: The bibliography/references block (`\begin{thebibliography}`) is excluded from the structural hierarchy and processed separately via reference extraction.
