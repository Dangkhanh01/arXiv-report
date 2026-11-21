# Milestone 2 — Hierarchical Parsing and Standardization

The parser recorded an outcome for all 27,608 expected versions and produced a clean parse for 25,037 of them. The course asks for a version-specific tree, a shared store of elements and a unified bibliography for each publication. {cite:p}`hcmus_statement_m2`

```{note}
**18,902 of 20,000 publications (94.51%) qualified for handoff.** Each expected version had to be cleanly parsed or confirmed empty, the stored tree had to pass validation, and all cited keys had to resolve. Eligibility applies to the whole publication.
```

## From a source archive to three tables

For each version, the parser follows the compilation path through the prepared LaTeX source and constructs a document tree. It then resolves bibliography entries across versions of the same publication, rewrites citation keys in the parsed content and standardizes each node. Three tables preserve the result.

The types and nullability below describe the exported Parquet schema. “Yes” means the field permits null. Keys describe how to identify and join rows.

### `elements` — one row per stored node

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `element_id` | string | No | Primary key. Combines the publication ID with a content-based suffix or a version-specific root suffix. |
| `arxiv_id` | string | No | Publication owning the node, written with a hyphen in the export, e.g. `2606-15734`. |
| `kind` | string | Yes | Node class, e.g. `document`, `section`, `paragraph`, `list`, `item`, `sentence`, `formula` or `figure`. Tables also use `figure`. |
| `content` | string | Yes | Normalized node content, such as a heading, sentence or LaTeX environment. A structural item can contain an empty string. |

### `hierarchy` — one row per edge in a version

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `arxiv_id` | string | No | Publication containing both endpoints. |
| `version` | int64 | Yes | Revision containing this edge, numbered from 1 by the writer. |
| `element_id` | string | No | Child node. Foreign key to `elements.element_id`. |
| `parent_id` | string | No | Parent node. Foreign key to `elements.element_id`. A root appears as a parent of its children and has no incoming edge. |

To reconstruct a tree, filter by publication and version, then join both endpoint IDs to `elements`. An unchanged child can appear in several versions' edge lists.

### `bibtex` — one row per unified reference in a publication

| Column | Type | Nullable | Description |
|---|---|:---:|---|
| `arxiv_id` | string | No | Citing publication. Together with `citation_key`, identifies the entry. |
| `citation_key` | string | No | Canonical key used by citations in the parsed text. |
| `entry_type` | string | Yes | BibTeX entry class, e.g. `article` or `inproceedings`. |
| `title` | string | Yes | Title of the cited work. |
| `authors` | list of strings | Yes | Ordered author names recovered from the bibliography. |
| `year` | int64 | Yes | Publication year. |
| `doi` | string | Yes | Digital object identifier of the cited work. |
| `journal` | string | Yes | Journal or conference venue. |
| `url` | string | Yes | Recorded URL for the cited work. |

## What qualified for export

The runner completed all 20,000 publication tasks across 12 account runs. A publication with only expected empty versions could qualify with zero elements. The handoff writer checked the ready marker, stored decision and artifacts before including a publication.

The manifests give one exclusion reason for each of the remaining 1,098 publications. Unresolved citations take precedence over partial or failed versions, so the exclusion counts describe the handoff decision. One publication can have additional diagnostics. The [statistics notebook](04_m2_stats.ipynb) shows the breakdown, the exported row counts and a lookup for every publication.

The [parsing chapter](02_parsing.md) follows a two-version paper from source files to a sentence. The [standardization chapter](03_standardization.md) follows that sentence across revisions.

## Team responsibilities

| Member | Milestone 2 responsibility |
|---|---|
| Khánh | Verify the M1 input inventory, identify compilation roots, follow the include graph and reconcile version coverage. |
| Khang | Build the document hierarchy, identify leaves and list items, and protect sentence boundaries. |
| Nguyên | Extract library and inline bibliography entries, merge reference metadata and produce a citation-key map for each version. |
| Danh | Apply citation-key maps, clean text and normalize math, deduplicate elements across versions, integrate the pipeline and measure its performance. |
