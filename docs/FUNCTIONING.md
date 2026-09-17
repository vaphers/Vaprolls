# System Architecture and Technical Functioning

## 1. Overview and Core Purpose

Vaprolls is a high-density, single-page technical SEO Spider and URL Explorer. It is built to perform comprehensive site crawls, map all encountered resources (HTML documents, CDN files, scripts, stylesheets, and images), and expose actionable diagnostic data through an interactive, split-panel spreadsheet interface.

---

## 2. End-to-End Processing Workflow

```
[Target URL]
     │
     ▼
[Crawl Engine] ──(Async Workers)──► [HTTP Fetcher / httpx]
     │                                     │
     ├─────────────────────────────────────┴───► [Raw HTML / Headers]
     ▼                                                  │
[Analyzers Pipeline] ◄──────────────────────────────────┘
  ├─ Technical, On-Page, and Directives Analyzers
  ├─ Link Architecture & PageRank Graph Engine
  ├─ Media, Images, and Responsive Asset Auditing
  ├─ Security, HTTPS, and Security Headers Validation
  ├─ Structured Data, Open Graph, and Twitter Cards
  ├─ Internationalization (Hreflang) & Pagination
  ├─ Accessibility (WCAG 2.0/2.1/2.2) Auditing
  ├─ Performance, Core Web Vitals, and CrUX Telemetry
  ├─ JavaScript SEO & Dynamic DOM Diffing
  └─ Content Quality, Readability, and SimHash Duplicate Detection
     │
     ▼
[Database Layer] (SQLite WAL Mode: 18 relational tables)
     │
     ├─► [Real-Time WebSocket Streamer] ──► [UI Progress Bar]
     ▼
[Master Enrichment Engine] (Unifies Pages + Discovered Assets + Links)
     │
     ▼
[Spider Explorer Single-Page Interface]
  ├─ Top Command Bar (Start / Stop Crawl, Mode Switcher, Quick Export)
  ├─ Category Tabs Bar (22 Tabs grouped into Overview, On-Page, Technical, Links, Auditing, Assets)
  ├─ Secondary Filter Bar (Include Regex, Exclude Regex, Live Search, Type Filter)
  ├─ Master Spreadsheet (Sticky headers, sortable columns, full URL wrapping)
  ├─ Draggable Bottom Inspector (URL Details, Inlinks, Outlinks, Images, SERP, Headers, Schema)
  └─ Draggable Right Panel (Issues Summary, Site Structure Tree, Response Times, Depth, Segments)
```

---

## 3. Core Subsystems

### 3.1 Asynchronous Crawl Engine (`crawler/engine.py`)
- **Queue and Worker Management**: Uses `asyncio.Queue` with configurable concurrency (default: 15 workers) to maximize network throughput without CPU exhaustion.
- **Normalization and Deduplication**: Normalizes URLs (scheme unification, trailing slash handling, fragment stripping) and tracks visited URLs in an in-memory hash set.
- **Policy Enforcement**:
  - Parses `robots.txt` using standard robot exclusion rules.
  - Resolves redirect chains up to 10 hops, recording the intermediate and final URLs.
  - Implements exponential backoff on network timeouts and rate-limiting responses (HTTP 429).

### 3.2 Analysis Pipeline (`analyzers/`)
- **Technical Analyzer (`analyzers/technical.py`)**: Evaluates HTTP status codes, protocol versions, content types, canonical link element parity, and robots meta tags (`noindex`, `nofollow`).
- **On-Page Analyzer (`analyzers/onpage.py`)**: Parses the DOM via `BeautifulSoup` (`lxml` parser) to extract title tags, meta descriptions, full heading hierarchy (H1, H2, H3), and visible word count.
- **Link Analyzer (`analyzers/links.py`)**: Analyzes all internal and external anchors, identifying target URLs, anchor text, follow/nofollow directives, and broken link patterns.
- **Media Analyzer (`analyzers/images.py`)**: Detects images, extracts source URLs (including responsive `srcset`), checks for missing alt text, evaluates dimensional attributes, and flags lazy loading implementation.
- **Structured Data Analyzer (`analyzers/structured_data.py`)**: Parses JSON-LD scripts and schema.org microdata, validating structure and entity typing.

### 3.3 Data Persistence (`database/db.py`)
- Built on `aiosqlite` with Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) for concurrent read/write stability.
- Normalized relational schema:
  - `audits`: Crawl metadata, root domain, configuration JSON, execution timestamps.
  - `pages`: Crawled page records, status codes, on-page SEO attributes, response times.
  - `links`: Directed link graph edges connecting source and destination URLs.
  - `images`: Image assets, dimensions, alternative text, and parent page associations.
  - `issues`: Diagnosed technical issues categorized by severity (Critical, High, Medium, Low).
  - `structured_data`: Parsed JSON-LD schemas and validation state.

### 3.4 WebSocket Real-Time Progress (`web/app.py`)
- Active audits stream live progress messages over `/ws/audit/{audit_id}`.
- Payload includes `crawled` count, `total` discovered count, and current processing URL.
- The frontend updates the top progress bar and percentage display in real time without polling.

---

## 4. Master URL Dataset Specification (The 11 Columns)

When viewing the **All URLs** master tab, the spreadsheet renders exactly 11 technical attributes for every mapped item:

| # | Column Name | Source Field | Description |
| :--- | :--- | :--- | :--- |
| 1 | **#** | Row Index | 1-based sequential row identifier |
| 2 | **Address** | `url` | Full URL string with complete text wrapping (`break-all`, no ellipsis truncation) |
| 3 | **Content Type** | `content_type` | Detected MIME type (e.g. `text/html`, `image/png`, `application/javascript`) |
| 4 | **Status Code** | `status_code` | HTTP response status code (color-coded by HTTP class) |
| 5 | **Status** | `status` | HTTP status explanation (e.g. `OK`, `Moved Permanently`, `Not Found`) |
| 6 | **Indexability** | `indexability` | Binary classification: `Indexable` or `Non-Indexable` |
| 7 | **Indexability Status** | `indexability_status` | Precise diagnostic reason (e.g. `OK`, `Canonicalised`, `Noindex`, `Resource / Image`) |
| 8 | **Hash** | `content_hash` | MD5 content hash of the document or asset |
| 9 | **Length** | `length` | Size of the document or asset payload in bytes |
| 10 | **Canonical Link Element** | `canonical_url` | Explicit canonical URL found in HTML tags or HTTP headers |
| 11 | **URL Encoded Address** | `url_encoded_address` | Full percent-encoded URI string |

---

## 5. User Interface Architecture

### 5.1 Single-Page Application (SPA) Design
- Multi-page landing structures and sidebars are eliminated.
- The root route (`/`) serves the complete interactive workspace, loading the latest audit or remaining in a ready state.
- Outer layout uses zero outer margins (`m-0 p-0`) and 1px structural dividers (`#D1D5DB`).

### 5.2 Draggable Split-Panel Layout
- **Vertical Resizer (`#inspector-resizer`)**:
  - Sits between the master URL table and the bottom inspector panel.
  - Supports click-and-drag height adjustment between 120px and 75% of viewport height.
  - Automatically saves the user's chosen height to `localStorage` (`spider_inspector_height`).
- **Horizontal Resizer (`#sidebar-resizer`)**:
  - Sits between the primary table/inspector section and the right sidebar.
  - Supports click-and-drag width adjustment between 240px and 60% of viewport width.
  - Automatically saves the user's chosen width to `localStorage` (`spider_sidebar_width`).

### 5.3 URL-Specific Inspection Logic
- When a user clicks any row in the master table:
  1. The row highlights with `#E5E7EB`.
  2. Bottom Inspector updates its 7 sub-tabs: `URL Details`, `Inlinks`, `Outlinks`, `Image Details`, `SERP Snippet`, `HTTP Headers`, `Structured Data`.
  3. Right Sidebar updates its **URL Overview** tab (Status, Canonicals, Length, Word Count, Inlinks, Outlinks, Title, Meta Description, H1) and **URL Issues** tab (all issues diagnosed for that specific URL).

### 5.4 Live Include and Exclude Filtering
- Supports client-side live filtering as characters are typed:
  - **Include Filter**: Evaluates regular expressions or substrings against the `url` field.
  - **Exclude Filter**: Filters out any URLs matching the supplied pattern.
  - **Search**: Scans text across table columns.
  - **Type Filter**: Narrows table down to HTML, JavaScript, CSS, Images, or PDF.

---

## 6. Lifecycle Management and Clean Shutdown

The application uses FastAPI's `lifespan` context manager:
- **SIGINT / SIGTERM / Shutdown Handling**:
  - Actively running background crawler tasks in `active_audits` are safely canceled.
  - Active WebSocket client connections are closed with code `1001` (Going Away).
  - Open SQLite database connections are committed and closed.
- **Manual Stop API**:
  - `POST /api/audit/{audit_id}/stop` terminates in-flight workers and marks the audit status as `stopped`.
