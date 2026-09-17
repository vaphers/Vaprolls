# Master URL Dataset & Tab Specifications

## 1. Dataset Overview

The master URL dataset is the core data model powering the interactive workspace. Unlike simple web crawlers that only index HTML pages, Vaprolls builds a unified, multi-tab database covering **every single discovered entity**—including HTML pages, CDN-hosted media, static stylesheets, scripts, font assets, and external outbound links.

The dataset engine is implemented in `web/enrichment.py` and provides 22 categorized tabs, dynamic heading expansion, right sidebar aggregations, and detailed inspector sub-tabs.

Related documentation:
- Discovery pipeline: [Crawler Engine](crawler_engine.md)
- Analysis algorithms: [Analysis Pipeline](analysis_pipeline.md)
- Workspace interface: [Frontend Workspace](frontend_workspace.md)
- Storage schema: [Database Architecture](database_architecture.md)

---

## 2. The 22 Category Tabs

The interface organizes data into 22 primary tabs divided across 6 functional category groups:

| Group | Tabs Included |
| :--- | :--- |
| **Overview** | `All URLs` (`all`), `Internal` (`internal`), `External` (`external`), `Response Codes` (`response_codes`) |
| **On-Page SEO** | `Page Titles` (`page_titles`), `Meta Description` (`meta_description`), `Meta Keywords` (`meta_keywords`), `H1` (`h1`), `H2` (`h2`), `Content` (`content`) |
| **Technical SEO** | `Canonicals` (`canonicals`), `Pagination` (`pagination`), `Directives` (`directives`), `Hreflang` (`hreflang`), `JavaScript` (`javascript`), `Sitemaps` (`sitemaps`) |
| **Links & Equity** | `Links` (`links`), `Security` (`security`), `Custom Search` (`custom_search`) |
| **Auditing & Health** | `Structured Data` (`structured_data`), `Accessibility` (`accessibility`) |
| **Assets** | `Images` (`images`) |

---

## 3. The 11 Master Columns (All URLs Tab)

When viewing the **All URLs** master tab, the spreadsheet exposes 11 columns in the following sequence:

| # | Display Header | Technical Key | Description |
| :---: | :--- | :--- | :--- |
| **1** | **#** | `row` | 1-based sequential row identifier. |
| **2** | **Address** | `url` | Fully qualified URL string, rendered with `break-all` text wrapping to guarantee full visibility without truncation. |
| **3** | **Content Type** | `content_type` | Detected MIME type (e.g. `text/html; charset=utf-8`, `image/png`, `application/javascript`, `text/css`). |
| **4** | **Status Code** | `status_code` | Numeric HTTP status code (200, 301, 404, 500, etc.). |
| **5** | **Status** | `status` | Descriptive HTTP status string (e.g. `OK`, `Moved Permanently`, `Not Found`). |
| **6** | **Indexability** | `indexability` | Binary classification: `Indexable` or `Non-Indexable`. |
| **7** | **Indexability Status** | `indexability_status` | Detailed diagnostic reason (e.g. `OK`, `Canonicalised`, `Noindex`, `Resource / Image`, `Client Error (404)`). |
| **8** | **Canonical Status** | `canonical_status` | State of the canonical link: `OK`, `Missing`, `Canonicalised`, or `Relative`. |
| **9** | **Canonical Link Element** | `canonical_url` | Declared canonical URL from `<link rel="canonical">` or HTTP headers. |
| **10** | **Internal PageRank** | `internal_pagerank` | Computed internal link equity score (0.00 to 100.00). |
| **11** | **Length** | `length` | Payload size of the document or asset in bytes. |

---

## 4. Tab Schema Specifications

Each of the 22 tabs renders a customized schema optimized for specific technical investigations:

### 4.1 Internal Tab (`internal`)
Exposes 33 technical metrics for every internal document:
- Row index, Address, Content Type, Status Code, Status.
- Indexability, Indexability Status, Canonical Status.
- Title 1, Title 1 Length, Meta Description 1, Description 1 Length.
- Dynamic H1 and H2 columns (dynamically expanded up to the maximum count found on any page).
- Canonical Link Element, Internal PageRank.
- Size, Transferred, Total Transferred bytes.
- Word Count, Sentence Count, Avg Words/Sentence, Text Ratio.
- Crawl Depth, Folder Depth.
- Inlinks, Unique Inlinks, Outlinks, Unique Outlinks.
- Response Time (ms), Redirect URL, Language, HTTP Version, Mobile Alt Link, Crawl Timestamp.

### 4.2 External Tab (`external`)
Tracks all external outbound hyperlinks:
- Address, Content Type, Status Code, Status, Crawl Depth, Inlinks count.

### 4.3 Response Codes Tab (`response_codes`)
Filters URLs by HTTP response classification:
- Address, Content Type, Status Code, Status, Indexability, Inlinks, Response Time, Redirect URL, Redirect Type.

### 4.4 Page Titles Tab (`page_titles`)
Audits title tags across all pages:
- Address, Title 1, Title 1 Length, Title 1 Pixel Width.
- Title 2 (if duplicate title tags exist).

### 4.5 Meta Description Tab (`meta_description`)
Audits meta description declarations:
- Address, Description 1, Description 1 Length, Description 1 Pixel Width.
- Description 2 (if duplicate descriptions exist).

### 4.6 H1 and H2 Tabs (`h1`, `h2`)
Evaluates heading structure and hierarchy:
- Address, H1-1 / H2-1 text and length.
- Dynamic additional heading columns (H1-2, H1-3, H2-2, H2-3, etc.) when multiple instances exist on a single document.

### 4.7 Content Tab (`content`)
Textual depth, readability, and duplicate copy evaluation:
- Address, Word Count, Sentence Count, Avg Words/Sentence, Text Ratio.
- Flesch Reading Ease score, Readability Label.
- Content Hash (MD5), Near Duplicate Hash (SimHash).
- Near Duplicate Count, Closest Duplicate URL, Similarity Percentage.

### 4.8 Images Tab (`images`)
Comprehensive image asset directory:
- Address (image source URL), Content Type, Status Code, Status.
- Size (bytes), Inlinks (referencing pages).
- Alt Text, Alt Text Length, Has Dimensions (`width`/`height` presence), Lazy Loaded.

### 4.9 Canonicals Tab (`canonicals`)
Detailed canonical link audit:
- Address, Canonical Link Element, Canonical Status (`Self-Referential`, `Canonicalised`, `Missing`, `Multiple`, `Relative`).

### 4.10 Directives Tab (`directives`)
Indexing and crawling directives:
- Address, Meta Robots, X-Robots-Tag, Indexability, Indexability Status.

### 4.11 Pagination Tab (`pagination`)
Sequential pagination series:
- Address, Rel Next URL, Rel Prev URL, Canonical URL, Sequence Status.

### 4.12 Hreflang Tab (`hreflang`)
Internationalization and localized tagging:
- Address, Language/Region Code, Alternate URL, Bidirectional Confirmation Status.

### 4.13 JavaScript Tab (`javascript`)
Client-side rendering comparisons:
- Address, Raw HTML Word Count, Rendered Word Count, Word Count Difference, JS Word Count Percentage.
- Raw vs Rendered Title, Raw vs Rendered H1, Raw vs Rendered Canonical.
- JS Console Errors, Warnings, Info, and Debug message counts.

### 4.14 Links Tab (`links`)
Link graph metrics:
- Address, Inlinks, Unique Inlinks, Outlinks, Unique Outlinks, External Outlinks, Link Equity Score.

### 4.15 Security Tab (`security`)
Security headers and protocol checks:
- Address, Protocol (HTTP vs HTTPS), Mixed Content presence.
- HSTS, Content Security Policy, X-Frame-Options, X-Content-Type-Options, Referrer Policy.

### 4.16 Structured Data Tab (`structured_data`)
Semantic markup schemas:
- Address, Schema Type, Schema Format (JSON-LD, Microdata, RDFa), Validation Status, Error Details.

### 4.17 Sitemaps Tab (`sitemaps`)
XML sitemap coverage and orphan page audit:
- Address, Found in Sitemap, Sitemap URL, Last Modified timestamp, Frequency, Priority.

### 4.18 Accessibility Tab (`accessibility`)
WCAG compliance checks:
- Address, Violations Total, Best Practice count, WCAG 2.0 Level A, Level AA, Level AAA, WCAG 2.1 AA, WCAG 2.2 AA.

### 4.19 Custom Search Tab (`custom_search`)
Results of user-defined search and regex extraction rules:
- Address, Rule Name, Match Status, Matched Snippet, Extracted Text.

---

## 5. Asset Enrichment Engine (`enrich_base_page_data`)

The dataset is constructed by merging crawled page records with auxiliary asset tables:
1. **HTML Page Records (`pages`)**: Core documents crawled directly by the engine.
2. **Discovered Image Assets (`images`)**: Extracted images, responsive `srcset` candidates, and external CDN media (Shopify CDN, Cloudflare Images). Assigned virtual identifiers `>= 100000`.
3. **Discovered Resource Links (`links`)**: Stylesheets (`.css`), scripts (`.js`), font assets (`.woff`, `.woff2`), and external hyperlinks. Assigned virtual identifiers `>= 100000`.

### Non-HTML Asset Inference Rules
- Images (`.png`, `.jpg`, `.jpeg`, `.webp`, `.svg`, `.avif`) -> Content Type: `image/*`, Indexability: `Non-Indexable`, Status: `Resource / Image`.
- Stylesheets (`.css`) -> Content Type: `text/css`, Indexability: `Non-Indexable`, Status: `Resource / CSS`.
- Scripts (`.js`, `.mjs`) -> Content Type: `application/javascript`, Indexability: `Non-Indexable`, Status: `Resource / JS`.
- External Outbound URLs -> Content Type: `external`, Indexability: `Non-Indexable`, Status: `External Link`.

---

## 6. Real-Time Filtering & Pagination Engine

The dataset supports both client-side and server-side filtering:
- **Type Filter**: Restricts view to HTML, JavaScript, CSS, Images, PDF, or Other.
- **Include Regex**: Evaluates regular expressions against URL addresses; only matching URLs remain visible.
- **Exclude Regex**: Excludes URLs matching the supplied pattern.
- **Live Search**: Instant substring search across visible columns.
- **Server-Side Pagination**: `/api/audit/{id}/tab/{tab_key}?page=1&page_size=500&sort_by=url&sort_dir=asc` returns sorted and paginated records efficiently.
