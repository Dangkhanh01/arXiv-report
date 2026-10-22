# Standardization & Cross-Version Deduplication

> [!NOTE]
> Standardization algorithms, regex patterns for `\bibitem` conversion, and deduplication compression statistics will be reported here in Milestone 2.

---

## 1. LaTeX Cleanup & Math Normalization

Unformatted LaTeX contains styling commands that distort natural language processing and semantic matching. Our cleanup pipeline standardizes the text:

1. **Stripping Formatting Commands**:
   - Visual placement specifiers: `[htpb]`, `[!t]`, `[pos]`.
   - Typography wrappers: `\centering`, `\raggedright`, `\midrule`, `\toprule`, `\bottomrule`.
   - Spacing commands: `\vspace{...}`, `\hspace{...}`, `\newpage`.
2. **Unified Mathematics Syntax**:
   - Inline equations are converted into standard `$...$` delimiters.
   - Block mathematical equations are unified into standard `\begin{equation}...\end{equation}` blocks.

---

## 2. Reference Extraction (`\bibitem` to BibTeX)

Citations embedded in the source as raw `\bibitem` entries are programmatically transformed into structured BibTeX format:

```text
Input (\bibitem):
\bibitem{vaswani2017} A. Vaswani et al., "Attention is all you need," NIPS 2017.

Output (BibTeX Table Row):
citation_key: vaswani2017
entry_type: inproceedings
title: Attention is all you need
authors: ["A. Vaswani", "others"]
year: 2017
```

---

## 3. Two-Tier Deduplication Across Versions

A central innovation in Milestone 2 is eliminating redundancy across paper revisions ($v_1, v_2, \dots, v_N$):

### Tier 1: Full-Text Content Deduplication
- When a sentence or formula block appears in multiple versions with identical cleaned content, it is assigned a **single unique `element_id`** in the `elements` table.
- Version-specific differences are reflected exclusively in the `hierarchy` table, which maps directed edges between `parent_id` and `element_id` for each version tree.

### Tier 2: Reference Entry Deduplication & Renaming
- If different versions assign different citation keys to the same publication, a canonical citation key is selected.
- All occurrences of `\cite{old_key}` across the `.tex` files are automatically renamed to `\cite{canonical_key}`.
- Fields across revisions are **unionized** (e.g., combining `title`, `author`, `year` from $v_1$ with `doi` added in $v_2$).
