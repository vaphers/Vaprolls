# Master URL Dataset Specification

## 1. Dataset Overview

The master URL dataset is the core data model displayed in the **All URLs** workspace tab. Unlike simple page crawlers that only display HTML pages, Vaprolls maps **every single discovered URL**—including HTML pages, CDN-hosted media, static stylesheets, JavaScript files, font assets, and external outbound links.

Related documentation:
- Discovery pipeline: [Crawler Engine](crawler_engine.md)
- Analysis algorithms: [Analysis Pipeline](analysis_pipeline.md)
- Workspace interface: [Frontend Workspace](frontend_workspace.md)

---

## 2. Specification of the 11 Required Columns

The master table strictly exposes 11 columns in the following sequence:

| Column # | Display Header | Technical Key | Type | Description |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **#** | `loop.index` | Integer | 1-based sequential row identifier. |
| **2** | **Address** | `url` | String (URI) | Fully qualified URL. Rendered with `break-all` text wrapping to guarantee full visibility without truncation or ellipsis. |
| **3** | **Content Type** | `content_type` | String | MIME type declaration (e.g. `text/html; charset=utf-8`, `image/png`, `application/javascript`, `text/css`). |
| **4** | **Status Code** | `status_code` | Integer | HTTP response status code (200, 301, 404, 500, etc.). |
| **5** | **Status** | `status` | String | HTTP status text description (e.g. `OK`, `Moved Permanently`, `Not Found`). |
| **6** | **Indexability** | `indexability` | String | Binary indexability status: `Indexable` or `Non-Indexable`. |
| **7** | **Indexability Status** | `indexability_status` | String | Specific technical reason (e.g. `OK`, `Canonicalised`, `Noindex`, `Resource / Image`, `Client Error (404)`). |
| **8** | **Hash** | `content_hash` | String | MD5 hash (first 12 to 16 characters) of the document content or URL string. |
| **9** | **Length** | `length` | Integer | Payload weight in bytes (HTML document size or media file size). |
| **10** | **Canonical Link Element** | `canonical_url` | String (URI) | Declared canonical URL from `<link rel="canonical">`. Renders `—` if not applicable. |
| **11** | **URL Encoded Address** | `url_encoded_address` | String (URI) | Complete percent-encoded representation of the URL (via `urllib.parse.quote`). |

---

## 3. Comprehensive Asset Mapping Engine (`enrich_pages_master`)

The master URL dataset is built by merging three distinct sources:
1. **Crawled HTML Pages**: Seed and interior pages fetched directly by the engine.
2. **Discovered Images (`all_images`)**: Media assets discovered across crawled pages, including CDN-hosted image assets (e.g. Shopify CDN, Cloudflare Images). Assigned synthetic IDs `>= 100000`.
3. **Discovered Resource Links (`all_links`)**: CSS stylesheets, external links, and JavaScript files extracted from DOM tags. Assigned synthetic IDs `>= 100000`.

### Content Type and Indexability Inference for Assets
For non-HTML assets, MIME types and indexability reasons are inferred from file extensions and DOM associations:
- Extensions `.png`, `.jpg`, `.webp`, `.svg` -> MIME `image/*`, Indexability `Non-Indexable`, Status `Resource / Image`.
- Extension `.css` -> MIME `text/css`, Indexability `Non-Indexable`, Status `Resource / CSS`.
- Extension `.js` -> MIME `application/javascript`, Indexability `Non-Indexable`, Status `Resource / JS`.
- External URLs -> Indexability `Non-Indexable`, Status `External Link`.

---

## 4. Include and Exclude Filtering Engine

The master table provides real-time client-side and server-side filtering:
- **Include Filter (`#include-filter-input`)**: Evaluates user-supplied regular expressions or substrings against the `url` attribute. Only URLs matching the pattern remain visible.
- **Exclude Filter (`#exclude-filter-input`)**: Evaluates regular expressions or substrings. Any URLs matching the pattern are hidden immediately.
- **Client-Side Execution**: Evaluated via `applyFiltersLive()` on every keypress without triggering page reloads.
- **Server-Side Execution**: Applied via `filter_and_sort_pages()` in `web/app.py` when exporting CSV datasets or bookmarking filter states.
