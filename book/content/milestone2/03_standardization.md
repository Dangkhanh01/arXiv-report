# Standardization and cross-version deduplication

## Cleaning the parsed content

The parser first maps citation keys to the unified bibliography for the publication. It then normalizes math and cleans each node before calculating its element ID. For example, the inline expression `\(x_i\)` becomes `$x_i$`, and the display expression `\[x_i = 0\]` becomes `\begin{equation}x_i = 0\end{equation}`. Multi-line alignment retains its internal structure in the equation wrapper. Literal code spans are protected. Cleaning removes presentation commands such as `\centering` and unwraps text formatting while retaining the enclosed words.

## Sharing a sentence between revisions

For a non-root node, the store constructs the ID below. The signature is the first **20 hexadecimal characters (80 bits)** of a SHA-256 digest. The two NUL separators delimit the three fields before UTF-8 encoding. Python's `hexdigest()` supplies the hexadecimal representation. {cite:p}`python_hashlib`

```python
from hashlib import sha256

def element_id(arxiv_id, kind, normalized_content, ordinal):
    publication = arxiv_id.strip().replace(".", "-")
    payload = f"{kind}\0{normalized_content.strip()}\0{ordinal}"
    signature = sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:20]
    return f"{publication}#{kind}-{signature}"
```

The ordinal starts at zero for each `(kind, content)` pair in each version. If “See Figure 1.” occurs twice as a sentence, its ordinals are 0 and 1. This gives each occurrence its own position in the tree. When a revision repeats both sentences, its ordinals start at zero again, allowing the corresponding occurrences to share IDs across versions. A document root uses the separate form `<publication>#root-v<version>`.

In **2606.15734**, the “ReGrad shifts adaptation cost” sentence from the [parsing example](02_parsing.md) has one element row and an edge in each of v1 and v2. Across the entire article, **1,035 node occurrences yield 522 stored elements**. The 1,033 hierarchy rows describe placements in the two trees. The two document roots have no incoming edges.

```{mermaid}
flowchart TD
    accTitle: Two version-specific edges reference one stored sentence
    subgraph hierarchy["hierarchy · one row per placement"]
        V1["v1 edge · Offline computation. → sentence"]
        V2["v2 edge · Offline computation. → sentence"]
    end
    subgraph elements["elements · one row for this sentence"]
        A["2606-15734#sentence-0e3369d51e665a3d2c12"]
    end
    V1 -->|child element_id| A
    V2 -->|child element_id| A
```

## Unifying references and rewriting citation keys

For each version, the extractor reads referenced BibTeX libraries, compiled bibliography records and inline `\bibitem` entries as available. It recovers fields such as title, authors, year and DOI from each source. Matching can use a shared DOI or arXiv identifier, a compatible normalized title, or a compatible citation key across revisions. Conflicting identifiers constrain merges. Ambiguous same-version keys are recorded for review.

The selected key favors a key used in the latest version of the group. The merger fills missing fields from other records and prefers recent values when combining metadata. A DOI supplied only in v1 can still appear in the unified row.

```{tip}
**Rewrite citation keys before hashing.** Suppose two records share a DOI. In v1 a sentence reads `We follow \cite{Smith20}.`, and in v2 it reads `We follow \cite{smith_bert_2020}.` Hashing these strings directly would produce different signatures. The v1 key map first rewrites `Smith20` to `smith_bert_2020` in the parsed node. After math normalization and cleanup, the two sentences have identical hash input for the same occurrence number. One element row can then serve both versions.
```

The two versions of **2606.15734** supplied **150 BibTeX source records** and yielded **73 unified entries**. One stored entry, `2021arXiv210100027G`, carries the DOI `10.48550/arxiv.2101.00027`. Across the corpus, the [statistics notebook](04_m2_stats.ipynb) compares the working counts before and after both deduplication steps and reports the rows that passed the publication-level export decision.
