# Technical Methodology & Pipeline Implementation

This section details the architectural decisions, API implementations, and reliability strategies that govern our Milestone 1 collection engine.

---

## 1. Targeted Discovery via OAI-PMH `arXivRaw`

### Why OAI-PMH `arXivRaw` over Query API or RSS?
The arXiv repository provides several discovery interfaces: the Query API (`/api/query`), RSS feeds, and the Open Archives Initiative Protocol for Metadata Harvesting (OAI-PMH). We chose the official OAI-PMH endpoint (`https://oaipmh.arxiv.org/oai`) using the `GetRecord` verb and the specialized `metadataPrefix=arXivRaw` for three decisive reasons:

1. **Full Version History in One Request**: Standard metadata formats (like Dublin Core or `arXiv`) return only the metadata of the latest version. In contrast, `arXivRaw` encodes the complete history of all versions ($v_1, v_2, \dots, v_N$) within its `<version>` tags.
2. **True Canonical Submission Dates**: The standard OAI `datestamp` header records the date metadata was updated, *not* when the research was submitted. Relying on `datestamp` introduces severe date distortion. `arXivRaw` stores the authentic timestamp of initial submission inside the $v_1$ version element.
3. **Deterministic Error Handling**: Protocol errors such as `idDoesNotExist` or `deleted` are explicitly structured in XML, distinguishing a non-existent paper from network transit errors.

```text
Request Pattern:
GET https://oaipmh.arxiv.org/oai?verb=GetRecord&metadataPrefix=arXivRaw&identifier=oai:arXiv.org:{arxiv_id}
```

---

## 2. Full-Text Source Extraction & Figure Removal

### Safe In-Memory Inspection & Extraction
Source archives are fetched from the versioned export mirror:
```text
GET https://export.arxiv.org/src/{arxiv_id}v{version}
```

The payload may be a compressed tarball (`.tar.gz`), a direct gzip-compressed TeX file (`.gz`), or an uncompressed TeX source. To fulfill the course requirement of removing figure binaries without compromising text:

1. **Tarball Traversal without Full Extraction**: The downloader streams the archive into an in-memory or temporary buffer and inspects directory headers using Python's `tarfile` module.
2. **Strict Whitelist**: Only files ending with `.tex` and `.bib` are extracted. Binary formats (`.png`, `.jpg`, `.pdf`, `.eps`), style sheets (`.sty`, `.cls`), and compiled outputs (`.bbl`, `.aux`) are discarded prior to disk write.
3. **Integrity Preservation**: The contents of `.tex` files are written strictly byte-exact. Figure environments (`\begin{figure}`) and inclusion statements (`\includegraphics{...}`) are kept completely untouched because Milestone 2 requires them to detect document hierarchy.
4. **Handling `no_tex` Records**: When an archive contains exclusively a PDF or DOCX binary with zero TeX sources, the pipeline records a valid `no_tex` event, creates an empty version folder, and generates a cryptographic receipt.

---

## 3. Reference Mining via Semantic Scholar Graph API

### Graph API Pagination & Separation of Stores
To acquire external citation metadata, the pipeline queries the Semantic Scholar Academic Graph API:
```text
GET https://api.semanticscholar.org/graph/v1/paper/ARXIV:{arxiv_id}/references?fields=title,authors,externalIds,publicationDate,year,venue&limit=100
```

1. **Complete Pagination**: The client systematically follows the `next` token returned by the API until the entire reference list is exhausted.
2. **Dual-Store Architecture**:
   - `references_all.json`: Stores **every single citation** returned by S2, including non-arXiv books, websites, unresolved papers, and duplicates.
   - `references.json`: Serves as the clean, filtered matching pool for Milestone 3, retaining only references with a verified `arxiv_id`.
3. **Canonical Date Resolution**: Rather than trusting Semantic Scholar's generic `publicationDate`, each cited arXiv ID is cross-referenced through an indexed Kaggle snapshot or OAI discovery to attach its authentic $v_1$ submission date.

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

The table below documents the strict production parameters configured across our crawling nodes:

| Parameter | Operational Setting | Rationale / Specification |
|:---|:---:|:---|
| `ARXIV_PACING_DELAY` | `3.1 seconds` | Complies with arXiv Terms of Use (mandatory ≥ 3.0s between requests) |
| `S2_PACING_DELAY` | `1.0 second` | Complies with Semantic Scholar Public API tier rate limits |
| `HTTP_MAX_RETRIES` | `5 attempts` | Exponential backoff ($t = 2.0 \times 2^{\text{attempt}}$, max 60s) on HTTP 429/503 |
| `CHECKPOINT_INTERVAL` | `40 papers` | Periodic immutable archive snapshot & SHA-256 receipt generation |
| `CACHE_TTL` | `24 hours` | Local XML and citation response verification cache |
| `SOURCE_WHITELIST` | `.tex, .bib, .bbl, .sty, .cls` | Excludes binary assets while preserving full LaTeX AST dependencies |

---

## 5. Architectural Module Mapping & Resilience Boundaries

### Software Module Mapping
Our codebase strictly modularizes core responsibilities:

| Operational Dimension | Source Module / Handler | Key Responsibilities |
|:---|:---|:---|
| **Discovery & Metadata** | `discovery.py::OaiClient` | `GetRecord` with `arXivRaw`, version parsing, initial submission date resolution |
| **Source Downloader** | `sources.py::SourceExtractor` | HTTP streaming, tarball in-memory traversal, selective whitelist extraction |
| **Citation Mining** | `references.py::S2Client` | Semantic Scholar Graph API pagination, `references_all` vs `references` partitioning |
| **Telemetry & Benchmarking**| `telemetry.py::ResourceSampler` | Background daemon sampling `psutil` process tree RSS and disk every 0.25s |
| **Durability & Checkpoints** | `checkpoints.py::CheckpointManager` | Atomic ZIP bundling, SHA-256 digest validation, Google Drive backup receipts |

### Resilience & Data Durability Boundaries
While the dual-backup architecture is engineered for high reliability in ephemeral Google Colab environments:
1. **Checkpoint Granularity**: Checkpoints commit in atomic increments of 40 papers. If a Colab session is preempted or terminated between checkpoints, at most 39 uncommitted papers must be re-crawled upon resumption.
2. **Idempotent Resumption**: When resuming a run, the pipeline inspects local and Drive commit receipts, seamlessly skipping all previously validated papers and versions without generating redundant upstream requests.
3. **Cryptographic Validation**: Every backup receipt stores exact SHA-256 digests and byte counts for both `corpus.zip` and `report.zip`, preventing archive corruption or incomplete tar stream writes.

