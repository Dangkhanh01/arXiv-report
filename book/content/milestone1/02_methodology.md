# Technical Methodology & Pipeline Implementation

This section details the architectural decisions, API implementations, and reliability strategies that govern our Milestone 1 collection engine.

---

## 1. Targeted Discovery via OAI-PMH `arXivRaw`

### Why OAI-PMH `arXivRaw` over Query API or RSS?
The arXiv repository provides several discovery interfaces: the Query API (`/api/query`), RSS feeds, and the Open Archives Initiative Protocol for Metadata Harvesting ([OAI-PMH v2.0](https://www.openarchives.org/OAI/openarchivesprotocol.html); Lagoze et al., 2002). We chose the official OAI-PMH endpoint (`https://oaipmh.arxiv.org/oai`) documented in the [arXiv OAI-PMH Service Guide](https://info.arxiv.org/help/oa/index.html) using the `GetRecord` verb and the specialized `metadataPrefix=arXivRaw` ([arXiv Metadata Formats](https://info.arxiv.org/help/oa/arXivRaw.html)) for three decisive reasons:

1. **Full Version History in One Request**: Standard metadata formats (like Dublin Core `oai_dc` or `arXiv`) return only the metadata snapshot of the latest version. In contrast, the `arXivRaw` schema exposes internal submission records encoding the complete history of all versions ($v_1, v_2, \dots, v_N$) within individual `<version>` elements.
2. **True Canonical Submission Dates**: Under Section 2.5 of the [OAI-PMH Protocol Specification](https://www.openarchives.org/OAI/openarchivesprotocol.html#RecordControlInfo), the standard OAI `datestamp` header indicates the date metadata was last modified or re-indexed in the repository, *not* when the research was submitted. Relying on `datestamp` introduces severe temporal distortion. `arXivRaw` stores the authentic timestamp of initial submission inside the `<version version="v1"><date>` element.
3. **Deterministic Error Handling**: Protocol-level error codes defined in the OAI-PMH standard (such as `idDoesNotExist` or `cannotDisseminateFormat`) are returned as structured XML elements, allowing the crawler to distinguish a non-existent paper from transient network failures.

```text
Request Pattern:
GET https://oaipmh.arxiv.org/oai?verb=GetRecord&metadataPrefix=arXivRaw&identifier=oai:arXiv.org:{arxiv_id}
```

---

## 2. Full-Text Source Extraction & Figure Removal

### Streamed Download and Selective Extraction
Source archives are fetched from the versioned export mirror following the [arXiv Source Download Specification](https://info.arxiv.org/help/faq/tarball.html):
```text
GET https://export.arxiv.org/src/{arxiv_id}v{version}
```

As documented in [arXiv Media Types](https://info.arxiv.org/help/mimetypes.html), the payload may be a compressed tarball (`.tar.gz`), a direct gzip-compressed TeX file (`.gz`), or a PDF-only submission. To fulfill the course requirement of removing figure binaries without compromising text:

1. **Tarball Traversal without Full Extraction**: The downloader streams the response to a temporary payload on disk. Gzip payloads are expanded to a bounded temporary file; `tarfile` then inspects members and writes only accepted source files. Temporary payloads and expanded archives contribute to the tracked disk footprint.
2. **Strict Whitelist**: Only files ending with `.tex` and `.bib` are extracted. Binary formats (`.png`, `.jpg`, `.pdf`, `.eps`), style sheets (`.sty`, `.cls`), and compiled outputs (`.bbl`, `.aux`) are discarded prior to disk write, meeting the course data preparation requirements ([HCMUS CS TA, 2026](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/)).
3. **Integrity Preservation**: The contents of `.tex` files are written strictly byte-exact. Figure environments (`\begin{figure}`) and inclusion statements (`\includegraphics{...}`) are kept completely untouched because Milestone 2 requires them to detect document hierarchy.
4. **Handling `no_tex` Records**: When an archive contains exclusively a PDF or DOCX binary with zero TeX sources, the pipeline records a valid `no_tex` event, creates an empty version folder, and generates a cryptographic receipt.

---

## 3. Reference Mining via Semantic Scholar Graph API

### Graph API Pagination & Separation of Stores
To acquire external citation metadata, the pipeline queries the [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/api-docs/graph) (Kinney et al., 2023):
```text
GET https://api.semanticscholar.org/graph/v1/paper/ARXIV:{arxiv_id}/references?fields=title,authors,externalIds,publicationDate,year,venue&limit=100
```

1. **Complete Pagination**: The client systematically follows the cursor-based `next` token defined in the [Semantic Scholar References API](https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_get_paper_references) until the entire citation list is exhausted.
2. **Dual-Store Architecture**:
   - `references_all.json` / `references_all.csv`: Stores **every single citation** returned by Semantic Scholar (totaling 734,157 citations across the corpus), capturing books, external URLs, non-arXiv journals, and conference papers.
   - `references.json` / `references_agg.csv`: Stores the clean, filtered matching pool for Milestone 3, retaining only citations with a verified `arxiv_id` (totaling 366,416 citation records).
3. **Canonical Date Resolution**: Rather than trusting Semantic Scholar's generic `publicationDate` (which often reflects external publisher publication or estimated year), each cited arXiv ID is cross-referenced through indexed Kaggle snapshots or OAI discovery to attach its authentic $v_1$ submission date.

### Corpus Layout and Receipt Locations

The crawler's `paper_directory()` maps dots in paper IDs to hyphens. Source versions live under `sources/vN/`; their receipts are siblings of the version directories. The schematic below follows the implementation. Filenames inside each version are supplied by the author; `main.tex` and a `.bib` file are not guaranteed to exist.

```text
corpus/
├── 2601-23264/
│   ├── metadata.json                 # Publication metadata, including revision dates
│   ├── references.json               # Filtered arXiv matching pool
│   ├── references_all.json           # Every returned S2 reference
│   ├── .references_receipt.json
│   └── sources/
│       ├── .v1.receipt.json          # Non-empty JSON: status, sizes and file hashes
│       ├── v1/                      # Author-named .tex/.bib files, if present
│       ├── .v2.receipt.json
│       ├── v2/
│       ├── .v3.receipt.json
│       └── v3/
└── 2606-17012/
    ├── metadata.json
    ├── references.json              # Empty arXiv pool in this example
    ├── references_all.json          # Five references reported in paper counters
    └── sources/
        ├── .v1.receipt.json          # JSON receipt for validated no_tex outcome
        └── v1/                      # Empty source directory; receipt is outside
```

A `no_tex` result means that a validated payload yielded no usable TeX. It does not, by itself, identify the payload as PDF-only. The JSON receipt is not zero bytes; its retained-source byte count is zero. M2 must inspect each version and locate its compilation root rather than assume a standard filename.

---

## 4. Reliability, Rate Limiting & Fault Tolerance

```{mermaid}
sequenceDiagram
    participant Colab as Google Colab Runtime
    participant OAI as arXiv OAI-PMH
    participant Src as arXiv Export Mirror
    participant S2 as Semantic Scholar API
    participant Drive as Google Drive Storage

    Colab->>Drive: Pre-flight write check & mount
    loop Every Assigned Publication
        Colab->>OAI: GetRecord (arXivRaw) [Paced >= 3.1s]
        OAI-->>Colab: XML Metadata & Versions
        loop Every Version (v1..vN)
            Colab->>Src: Download Source [Paced >= 3.1s]
            Src-->>Colab: Tarball / TeX stream
            Colab->>Colab: Whitelist .tex/.bib only
        end
        Colab->>S2: Get References [Follow next pagination]
        S2-->>Colab: Citations payload
        alt Every 40 Papers
            Colab->>Drive: Background checkpoint (Immutable ZIP + SHA-256)
        end
    end
    Colab->>Drive: Final dual backup (Corpus ZIP + Report ZIP)
```

### Empirical Pipeline Configuration Parameters

The table below documents the production parameters configured across our crawling nodes (defined in the shared repo's `src/notebooks/milestone1.ipynb` and `src/crawling/pipeline.py`):

| Parameter | Operational Setting | Rationale / Specification |
|:---|:---:|:---|
| `ARXIV_PACING_DELAY` | `3.1 seconds` | Complies with [arXiv Terms of Use for APIs](https://info.arxiv.org/help/api/tou.html) (mandatory $\ge 3.0$s between consecutive requests to prevent IP throttling) |
| `S2_PACING_DELAY` | `3.1 seconds` | Conservative pacing adhering to [Semantic Scholar API Rate Limits](https://www.semanticscholar.org/product/api#api-faq) (avoids HTTP 429 rate limit triggers on public endpoints) |
| `HTTP_MAX_RETRIES` | `3 attempts` | Up to 3 total attempts; exponential backoff cap 120s, while server Retry-After takes precedence |
| `CHECKPOINT_INTERVAL` | `40 papers` | Periodic immutable archive snapshot & SHA-256 receipt generation for Colab durability |
| `CACHE_TTL` | `24 hours` | Local XML and citation response verification cache conforming to HTTP RFC 9111 caching standards |
| `SOURCE_WHITELIST` | `.tex, .bib` | Whitelist per [HCMUS CS TA Data Crawling Statement](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/); binary figures (.png, .jpg, .pdf) and auxiliary files (.bbl, .sty, .cls) excluded |

---

## 5. Architectural Module Mapping & Resilience Boundaries

### Software Module Mapping
The following symbols exist in the shared crawler at [commit 21d624e](https://github.com/Hireophant/arXivProject/tree/21d624e2a79e4c6d1a046a13ba0ad1e651fbbe9e/src/crawling). This mapping describes that implementation; historical runs may use earlier revisions:

| Operational Dimension | Implementation Module & Core Functions | Key Responsibilities |
|:---|:---|:---|
| **Discovery & Metadata** | `discover.py` (`OaiClient.fetch`, `OaiClient.discover`, `_parse_raw`) | `GetRecord` with `arXivRaw`, version parsing, initial submission date resolution |
| **Source Downloader** | `download.py` (`download_version`, `prepare_source`, `_extract_tar`) | HTTP streaming to temporary disk, bounded archive inspection and `.tex`/`.bib` extraction |
| **Citation Mining** | `references.py` (`collect_references`, `_request_s2`) | Semantic Scholar Graph API pagination, `all_references` vs `references` partitioning |
| **Telemetry & Benchmarking**| `metrics.py` (`collect_resource_samples`, `summarize_benchmark`, `summarize_corpus`) | Background daemon sampling `psutil` process tree RSS and disk every 0.25s |
| **Durability & Checkpoints** | `checkpoints.py` (`BackgroundCheckpoints.paper_done`, `BackgroundCheckpoints.close`, `BackgroundCheckpoints.finalize`) | Incremental ZIP bundling, SHA-256 digest validation, Google Drive backup receipts |

### Resilience & Data Durability Boundaries
While the dual-backup architecture is engineered for high reliability in ephemeral Google Colab environments:
1. **Checkpoint Granularity & Recovery Window**: Checkpoints commit in atomic increments of 40 papers. Because Google Colab runtimes can be preempted while a batch is actively being processed or uploaded, only checkpoints that have successfully committed their verification receipt to Google Drive are protected. Any uncommitted papers actively in transit must be re-crawled upon session resumption.
2. **Idempotent Resumption**: When resuming a run, the pipeline inspects local and Drive commit receipts, seamlessly skipping all previously validated papers and versions without generating redundant upstream requests.
3. **Cryptographic Validation**: Backup receipts store SHA-256 digests and byte counts for `corpus.zip` and `report.zip`. Comparing stored values to the actual archives detects transport mismatches; it does not prevent corruption or prove semantic correctness. The report aggregator now checks every selected report ZIP before ingestion. The historical measurement tables in this repository have not been revalidated against their original ZIPs during this correction because those input trees are unavailable locally.

