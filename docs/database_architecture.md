# Database Architecture Specification

## 1. Storage Engine Overview

Vaprolls uses an embedded SQLite database managed via `aiosqlite` in `database/db.py`. To ensure high concurrency without lock contention between asynchronous crawler workers, post-crawl analysis pipelines, and web frontend queries, the engine enables Write-Ahead Logging (WAL mode).

Related documentation:
- Ingestion subsystem: [Crawler Engine](crawler_engine.md)
- Analysis models: [Analysis Pipeline](analysis_pipeline.md)
- Telemetry endpoints: [API & WebSocket Protocol](api_and_websocket.md)
- Dataset structure: [URL Dataset Specification](url_dataset_specification.md)

---

## 2. SQLite Configuration Pragma Settings

Upon database connection initialization (`Database.init()`), the following pragmas are executed:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA temp_store = MEMORY;
```
- `journal_mode = WAL`: Write-Ahead Logging ensures readers do not block writers and writers do not block readers.
- `synchronous = NORMAL`: Flushes database writes to disk at critical sync points, balancing data durability with high insertion throughput during crawls.
- `cache_size = -64000`: Allocates 64MB of in-memory page cache per connection.
- `temp_store = MEMORY`: Directs temporary tables, sorting buffers, and intermediate query results to RAM.

---

## 3. Relational Schema Architecture

The database contains 18 relational tables organized around individual audit runs:

```
                                  ┌───────────────┐
                                  │    audits     │
                                  └───────┬───────┘
                                          │ 1:N
        ┌──────────────────┬──────────────┼──────────────┬──────────────────┐
        ▼                  ▼              ▼              ▼                  ▼
  ┌───────────┐      ┌───────────┐  ┌───────────┐  ┌───────────┐      ┌───────────┐
  │   pages   │      │   links   │  │  images   │  │  issues   │      │ resources │
  └─────┬─────┘      └───────────┘  └───────────┘  └───────────┘      └───────────┘
        │ 1:N
        ├──────────────────┬──────────────────┬──────────────────┐
        ▼                  ▼                  ▼                  ▼
  ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐
  │ headings  │      │ keywords  │      │ structured│      │perf_metric│
  └───────────┘      └───────────┘      │   _data   │      └───────────┘
                                        └───────────┘
```

---

## 4. Complete Table Specifications

### 4.1 Table: `audits`
Tracks audit lifecycle, configuration, and sitewide health score.
- `id` (TEXT, PK): UUID identifier.
- `domain` (TEXT): Root domain crawled.
- `url` (TEXT): Start seed URL.
- `started_at` (TIMESTAMP): Execution start timestamp.
- `completed_at` (TIMESTAMP): Execution completion timestamp.
- `status` (TEXT): `pending`, `crawling`, `analyzing`, `complete`, `stopped`, or `error`.
- `total_pages` (INTEGER): Total pages crawled.
- `total_issues` (INTEGER): Aggregate count of issues diagnosed.
- `health_score` (REAL): Computed overall health score (0.0 to 100.0).
- `config_json` (TEXT): Serialized crawl settings and AI enhancement outputs.

### 4.2 Table: `pages`
Master table containing all crawled URLs and enriched on-page metadata.
- `id` (INTEGER, PK AUTOINCREMENT): Primary page record ID.
- `audit_id` (TEXT, FK -> audits.id): Owning audit run.
- `url` (TEXT): Crawled URL address.
- `status_code` (INTEGER): HTTP response code (200, 301, 404, 500, etc.).
- `content_type` (TEXT): MIME type (e.g. `text/html; charset=utf-8`).
- `response_time_ms` (REAL): Server response time in milliseconds.
- `html_size` (INTEGER): Document payload size in bytes.
- `word_count` (INTEGER): Visible body text word count.
- `title` (TEXT): Page title tag text.
- `title_length` (INTEGER): Title length in characters.
- `title_pixel_width` (INTEGER): Estimated title pixel width in SERP snippets.
- `meta_description` (TEXT): Meta description text.
- `meta_description_length` (INTEGER): Meta description character count.
- `meta_desc_pixel_width` (INTEGER): Estimated description pixel width.
- `h1` (TEXT): Primary H1 heading text.
- `h1_count` (INTEGER): Total H1 elements found.
- `h2_count` (INTEGER): Total H2 elements found.
- `canonical_url` (TEXT): Canonical link element target.
- `is_indexable` (BOOLEAN): Indexability flag.
- `crawl_depth` (INTEGER): Number of clicks from the seed URL.
- `folder_depth` (INTEGER): URL path segment depth.
- `redirect_url` (TEXT): Final destination if redirected.
- `redirect_chain` (TEXT): Serialized list of redirect hops.
- `redirect_chain_details` (TEXT): Serialized redirect hop metadata (status, protocol, duration).
- `content_hash` (TEXT): MD5 hash of the HTML document.
- `content_near_duplicate_hash` (TEXT): 64-bit SimHash for near-duplicate copy detection.
- `internal_pagerank` (REAL): Computed Internal PageRank authority score (0.0 - 100.0).
- `raw_html_hash` (TEXT): MD5 hash before client-side JavaScript execution.
- `rendered_html_hash` (TEXT): MD5 hash after Playwright DOM rendering.
- `html_word_count` (INTEGER) / `rendered_word_count` (INTEGER): Static vs rendered word counts.
- `word_count_change` (INTEGER): Net word count difference from JavaScript rendering.
- `js_word_count_pct` (REAL): Percentage of content dependent on JavaScript.
- `sentence_count` (INTEGER) / `avg_words_per_sentence` (REAL): Textual readability metrics.
- `text_ratio` (REAL): Ratio of visible text to markup weight.
- `flesch_reading_ease` (REAL): Flesch reading score.
- `readability_label` (TEXT): Readability classification string.
- `unique_inlinks` (INTEGER) / `unique_outlinks` (INTEGER): Link connectivity counters.
- `headers_json` (TEXT) / `cookies_json` (TEXT): Full HTTP response headers and cookies.
- `og_title`, `og_description`, `og_image`, `og_type` (TEXT): Open Graph social metadata.
- `twitter_card`, `twitter_title`, `twitter_description`, `twitter_image` (TEXT): Twitter Card metadata.
- `hsts_header`, `csp_header`, `x_frame_options`, `x_content_type_options` (TEXT): Security headers.
- `tls_protocol`, `server_header` (TEXT): SSL/TLS version and web server identification.
- `has_mixed_content` (BOOLEAN): Indicates insecure resource inclusions.

### 4.3 Table: `links`
Stores all discovered hyperlink edges between pages.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `source_page_id` (INTEGER, FK -> pages.id)
- `source_url` (TEXT): URL where the link was found.
- `target_url` (TEXT): Destination URL.
- `anchor_text` (TEXT): Visible link anchor text.
- `link_type` (TEXT): `hyperlink`, `css`, `js`, `image`, or `canonical`.
- `rel` (TEXT): Rel attributes (`nofollow`, `sponsored`, `ugc`, `noopener`).
- `is_internal` (BOOLEAN): Internal domain vs external destination.
- `status_code` (INTEGER): Status code of target URL if verified.
- `is_broken` (BOOLEAN): Set to 1 if target returns 4xx/5xx.

### 4.4 Table: `images`
Stores media declarations, dimensions, and accessibility attributes.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `page_url` (TEXT): Page containing the image.
- `src` (TEXT): Resolved image source URL.
- `alt_text` (TEXT): Alternative text attribute value.
- `width` (INTEGER) / `height` (INTEGER): Explicit image dimensions.
- `has_dimensions` (BOOLEAN): Whether width and height attributes exist.
- `file_size` (INTEGER): Image payload weight in bytes.
- `content_type` (TEXT): MIME type (e.g. `image/webp`, `image/jpeg`).
- `is_broken` (BOOLEAN): Broken image indicator.
- `is_lazy_loaded` (BOOLEAN): Whether `loading="lazy"` is declared.

### 4.5 Table: `issues`
Diagnostic technical, on-page, and structural issues discovered across the site.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, Nullable, FK -> pages.id)
- `url` (TEXT): Affected page URL (or NULL for sitewide issues).
- `category` (TEXT): `technical`, `onpage`, `links`, `images`, `performance`, `security`, `accessibility`, etc.
- `severity` (TEXT): `critical`, `warning`, or `info`.
- `issue_type` (TEXT): Specific diagnostic code (e.g. `missing_h1`, `broken_link`, `missing_alt`, `noindex`).
- `message` (TEXT): Descriptive explanation of the issue.
- `recommendation` (TEXT): Actionable remediation instructions.
- `element` (TEXT): Affected HTML element, URL, or data payload.
- `created_at` (TIMESTAMP): Issue creation timestamp.

### 4.6 Table: `headings`
Stores full heading elements (H1 through H6) for structural document analysis.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `level` (INTEGER): Heading depth (1 for H1, 2 for H2, etc.).
- `text` (TEXT): Heading text content.
- `position` (INTEGER): Sequential occurrence index within the document.

### 4.7 Table: `resources`
Assets (stylesheets, scripts, fonts) associated with crawled pages.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `url` (TEXT): Asset URL.
- `resource_type` (TEXT): `css`, `js`, `font`, or `other`.
- `size` (INTEGER): Asset size in bytes.
- `is_render_blocking` (BOOLEAN): Indicates whether resource blocks initial page rendering.

### 4.8 Table: `keywords`
Stores extracted keyword n-grams and frequency data.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `keyword` (TEXT): Extracted term.
- `count` (INTEGER): Occurrence frequency on the page.
- `density` (REAL): Percentage density relative to total words.
- `in_title` / `in_meta` / `in_h1` (BOOLEAN): Placement indicators.
- `search_intent` (TEXT): `informational`, `commercial`, `transactional`, or `navigational`.

### 4.9 Table: `performance_metrics`
Detailed page-level loading and Web Vitals metrics.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `lcp_ms` (REAL): Largest Contentful Paint in milliseconds.
- `cls` (REAL): Cumulative Layout Shift score.
- `fcp_ms` (REAL): First Contentful Paint in milliseconds.
- `speed_index` (REAL): Speed Index value.
- `performance_score` (REAL): Overall performance score (0 - 100).
- `total_page_size` (INTEGER): Combined byte weight of all assets.
- `lighthouse_json` (TEXT): Full Lighthouse audit payload.

### 4.10 Table: `structured_data`
Semantic schemas parsed from documents.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `schema_type` (TEXT): Declared `@type` (e.g. `Product`, `Article`, `Organization`).
- `format` (TEXT): `json-ld`, `microdata`, or `rdfa`.
- `raw_json` (TEXT): Parsed JSON schema content.
- `is_valid` (BOOLEAN): Schema validation result.
- `errors` (TEXT): Validation error messages.

### 4.11 Table: `hreflang_tags`
Internationalization tags for localized versions.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `source_url` (TEXT): Page declaring the tag.
- `hreflang_code` (TEXT): Language/region code (e.g. `en-US`, `es`, `x-default`).
- `target_url` (TEXT): Alternate destination URL.
- `has_return_tag` (BOOLEAN): Whether bidirectional confirmation link exists.
- `is_self_referencing` (BOOLEAN): Whether tag links back to current page.

### 4.12 Table: `pagination_tags`
Sequential pagination tags (`rel="next"` / `rel="prev"`).
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `source_url` (TEXT): Current page URL.
- `rel_type` (TEXT): `next` or `prev`.
- `target_url` (TEXT): Paginated target URL.

### 4.13 Table: `forms`
Audited HTML form declarations and security postures.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `page_url` (TEXT): Page hosting the form.
- `action_url` (TEXT): Submission target URL.
- `method` (TEXT): `GET` or `POST`.
- `form_id` (TEXT): HTML element identifier or name.
- `has_password` (BOOLEAN): Indicates password input field.
- `is_insecure` (BOOLEAN): Indicates submission over plain HTTP.

### 4.14 Table: `external_links`
External outbound hyperlinks.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `source_page_id` (INTEGER, FK -> pages.id)
- `source_url` (TEXT): Source page.
- `target_url` (TEXT): External destination URL.
- `anchor_text` (TEXT): Anchor text.
- `rel_attributes` (TEXT): Declared rel values.
- `status_code` (INTEGER): Verified HTTP response code.
- `is_broken` (BOOLEAN): Whether external destination is broken.

### 4.15 Table: `sitemap_entries`
URLs parsed directly from XML sitemaps.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `sitemap_url` (TEXT): Parent sitemap file URL.
- `url` (TEXT): Declared page location (`<loc>`).
- `lastmod` (TEXT): Declared last modified timestamp.
- `changefreq` (TEXT): Change frequency value.
- `priority` (REAL): Declared priority value.

### 4.16 Table: `accessibility_violations`
Accessibility findings evaluated against WCAG rules.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `page_url` (TEXT): Target page URL.
- `rule_id` (TEXT): Specific WCAG rule identifier (e.g. `image-alt`, `color-contrast`).
- `wcag_level` (TEXT): `wcag_2_0_a`, `wcag_2_0_aa`, `wcag_2_0_aaa`, `wcag_2_1_aa`, `wcag_2_2_aa`, or `best_practice`.
- `impact` (TEXT): `critical`, `serious`, `moderate`, or `minor`.
- `message` (TEXT): Violation description.
- `html_snippet` (TEXT): Snippet of the failing markup.

### 4.17 Table: `custom_extractions`
User-defined CSS/XPath/Regex extraction results.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `rule_name` (TEXT): Defined rule identifier.
- `extracted_value` (TEXT): Extracted text content.

### 4.18 Table: `custom_searches`
User-defined text search matches and omissions.
- `id` (INTEGER, PK AUTOINCREMENT)
- `audit_id` (TEXT, FK -> audits.id)
- `page_id` (INTEGER, FK -> pages.id)
- `rule_name` (TEXT): Defined search rule identifier.
- `match_found` (BOOLEAN): Whether condition was satisfied.
- `matched_snippet` (TEXT): Extracted matching snippet.
