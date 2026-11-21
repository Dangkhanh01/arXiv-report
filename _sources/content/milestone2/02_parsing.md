# Hierarchical LaTeX parsing

## Finding the manuscript

A source directory can contain a main manuscript, several included chapters and an independent supplement. The gatherer inspects the include graph and the expanded candidates for a document declaration and body. It ranks independent candidates, checks for auxiliary files and groups candidates with identical expanded content and bibliography scope. If distinct plausible roots remain, it records the ambiguity. Missing inputs and include cycles also leave diagnostics.

Starting at the selected root, the gatherer follows active `\input` and `\include` commands, resolves paths and tracks used and unused files. Commented commands do not add a file. Bibliography lookup uses the compilation context of the version being parsed.

```{mermaid}
flowchart TD
    accTitle: Parsing one version of a publication
    A["Prepared source archive"] --> R["Find the main compilation root"]
    R --> I["Recursively resolve input and include commands"]
    I --> F["Flatten reachable TeX in compilation order"]
    F --> W["Walk structural blocks in the document body"]
    W --> H["Headings and list items"]
    W --> B["Display math, figures and tables"]
    W --> P["Prose spans"]
    P --> S["Split sentences, protecting math, URLs and abbreviations"]
    H --> T["Document tree for this version"]
    B --> T
    S --> T
```

For **2606.15734**, the recorded root in both versions was `acl_latex.tex`. Each traversal used that root plus `Table/main-top1000.tex`, `Table/Capability.tex` and `Table/ood.tex`. Both versions finished with status `parsed`.

## From headings to sentences

The parser walks the body in document order. Headings establish parents for subsections, paragraphs and their children. Lists contain item nodes. Display mathematics becomes a formula node. Figures and tables share the stored kind `figure`, which preserves the LaTeX environment and caption. Inline mathematics stays with its sentence. The sentence splitter protects math, command arguments, URLs, decimal numbers and common academic abbreviations. Bibliography material goes to reference extraction.

For example, splitting at the period in “Fig. 1” would detach the figure number from its sentence. Kiss and Strunk discuss the ambiguity between abbreviations and sentence endings. Our splitter handles this case by checking a fixed list that includes “Fig.” before accepting a period as a boundary. {cite:p}`kiss_strunk_2006`

This branch comes from the version 1 `hierarchy.jsonl` for **2606.15734**. Each label was recovered by joining the edge endpoints to `elements.jsonl`.

~~~text
Version 1 root
└── section · Efficiency Analysis
    └── paragraph · Offline computation.
        └── sentence · ReGrad shifts adaptation cost to the offline construction of the Gradient Bank.
~~~

The sentence has ID `2606-15734#sentence-0e3369d51e665a3d2c12`. Its parent has ID `2606-15734#paragraph-c93bd3f4807157b04b61`. The same child and parent occur in the version 2 edge list. Each version has its own document root.

### Where the bibliography ends

Acknowledgements and appendices remain in the document tree. References go to bibliography extraction. In the parser's regression example, a main bibliography is followed by `\appendix`, a section titled *Appendix method*, the sentence “Appendix sentence.” and the display formula `\[a = b\]`. A supplementary bibliography follows. The tree retains the appendix section, sentence and formula while excluding entries from both bibliographies. Parsing resumes at the end of the first bibliography. {cite:p}`hcmus_statement_m2`

## Interpreting incomplete trees

```{note}
A confirmed `empty_no_tex` version stays in the coverage denominator and contributes zero nodes. For example, the sole version of **2606.15742** was confirmed empty and the publication qualified for handoff. If upstream staging fails, the version receives `blocked_input` and its publication is excluded.
```

A `partial` version can contribute nodes to the working store, for example when the parser recovers prose but a cited key remains unresolved. A `failed` version can result when the parser finds no semantic content. Both states exclude the publication from handoff. The [coverage lookup](04_m2_stats.ipynb) exposes all five states per publication.
