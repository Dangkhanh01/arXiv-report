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

### Safe In-Memory Inspection & Extraction
Source archives are fetched from the versioned export mirror following the [arXiv Source Download Specification](https://info.arxiv.org/help/faq/tarball.html):
```text
GET https://export.arxiv.org/src/{arxiv_id}v{version}
```

As documented in [arXiv Media Types](https://info.arxiv.org/help/mimetypes.html), the payload may be a compressed tarball (`.tar.gz`), a direct gzip-compressed TeX file (`.gz`), or a PDF-only submission. To fulfill the course requirement of removing figure binaries without compromising text:

1. **Tarball Traversal without Full Extraction**: The downloader streams the archive into an in-memory buffer and inspects directory headers using Python's `tarfile` module.
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

### Concrete Corpus Organization Example

To verify downstream handoff readiness for Milestone 2 and Milestone 3, publications are organized uniformly on disk:

```text
corpus/
├── 2601.23264/                        # Multi-version paper (3 versions)
│   ├── metadata.json                 # OAI-PMH metadata & parsed version history
│   ├── references.json               # Filtered arXiv matching pool (kept_references)
│   ├── references_all.json           # All S2 citations (total_references)
│   ├── v1/
│   │   ├── main.tex                  # Extracted source file (figures excluded)
│   │   └── references.bib            # BibTeX bibliography
│   ├── v2/
│   │   └── main.tex
│   └── v3/
│       ├── main.tex
│       └── appendix.tex
└── 2606.17012/                        # Author PDF-only upload (no_tex event)
    ├── metadata.json                 # Canonical title & submission timestamp
    ├── references.json               # Citation list (5 total citations, 0 arXiv)
    ├── references_all.json           # Full Semantic Scholar response
    └── v1/                           # Validated no_tex terminal state
        └── .receipt.json             # Verification receipt (status: no_tex, 0 bytes)
```

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

The table below documents the production parameters configured across our crawling nodes (defined in `arXiv/src/notebooks/milestone1.ipynb` and `pipeline.py`):

| Parameter | Operational Setting | Rationale / Specification |
|:---|:---:|:---|
| `ARXIV_PACING_DELAY` | `3.1 seconds` | Complies with [arXiv Terms of Use for APIs](https://info.arxiv.org/help/api/tou.html) (mandatory $\ge 3.0$s between consecutive requests to prevent IP throttling) |
| `S2_PACING_DELAY` | `3.1 seconds` | Conservative pacing adhering to [Semantic Scholar API Rate Limits](https://www.semanticscholar.org/product/api#api-faq) (avoids HTTP 429 rate limit triggers on public endpoints) |
| `HTTP_MAX_RETRIES` | `3 attempts` | Exponential backoff capped at 120s upon receiving HTTP 429 / 503 retry-after headers |
| `CHECKPOINT_INTERVAL` | `40 papers` | Periodic immutable archive snapshot & SHA-256 receipt generation for Colab durability |
| `CACHE_TTL` | `24 hours` | Local XML and citation response verification cache conforming to HTTP RFC 9111 caching standards |
| `SOURCE_WHITELIST` | `.tex, .bib` | Whitelist per [HCMUS CS TA Data Crawling Statement](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/crawling/); binary figures (.png, .jpg, .pdf) and auxiliary files (.bbl, .sty, .cls) excluded |

---

## 5. Architectural Module Mapping & Resilience Boundaries

### Software Module Mapping
Our codebase (`arXiv/src/crawling/`) strictly modularizes core responsibilities across focused Python modules:

| Operational Dimension | Implementation Module & Core Functions | Key Responsibilities |
|:---|:---|:---|
| **Discovery & Metadata** | `discover.py` (`fetch_oai_record`, `parse_oai_record`) | `GetRecord` with `arXivRaw`, version parsing, initial submission date resolution |
| **Source Downloader** | `download.py` (`download_version`, `download_paper_versions`) | HTTP streaming, tarball in-memory traversal, selective whitelist extraction (`.tex`/`.bib`) |
| **Citation Mining** | `references.py` (`collect_references`, `fetch_references_page`) | Semantic Scholar Graph API pagination, `all_references` vs `references` partitioning |
| **Telemetry & Benchmarking**| `metrics.py` (`collect_resource_samples`, `summarize_run`) | Background daemon sampling `psutil` process tree RSS and disk every 0.25s |
| **Durability & Checkpoints** | `checkpoints.py` (`BackgroundCheckpoints`, `commit_checkpoint`) | Incremental ZIP bundling, SHA-256 digest validation, Google Drive backup receipts |

### Resilience & Data Durability Boundaries
While the dual-backup architecture is engineered for high reliability in ephemeral Google Colab environments:
1. **Checkpoint Granularity & Recovery Window**: Checkpoints commit in atomic increments of 40 papers. Because Google Colab runtimes can be preempted while a batch is actively being processed or uploaded, only checkpoints that have successfully committed their verification receipt to Google Drive are protected. Any uncommitted papers actively in transit must be re-crawled upon session resumption.
2. **Idempotent Resumption**: When resuming a run, the pipeline inspects local and Drive commit receipts, seamlessly skipping all previously validated papers and versions without generating redundant upstream requests.
3. **Cryptographic Validation**: Every backup receipt stores exact SHA-256 digests and byte counts for both `corpus.zip` and `report.zip`, preventing archive corruption or incomplete tar stream writes.

