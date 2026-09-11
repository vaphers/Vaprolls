# Database Architecture Specification

## 1. Storage Engine Overview

Vaprolls uses an embedded SQLite database managed via `aiosqlite` in `database/db.py`. To ensure high concurrency without lock contention between multiple asynchronous crawler workers and frontend read queries, the engine enables Write-Ahead Logging (WAL mode).

Related documentation:
- Ingestion subsystem: [Crawler Engine](crawler_engine.md)
- Analysis models: [Analysis Pipeline](analysis_pipeline.md)
- Telemetry endpoints: [API & WebSocket Protocol](api_and_websocket.md)

---

## 2. SQLite Configuration Pragma Settings

Upon database connection initialization (`Database.init()`), the following pragmas are executed:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA temp_store = MEMORY;
```
- `journal_mode = WAL`: Readers do not block writers, and writers do not block readers.
- `synchronous = NORMAL`: Balances data safety with disk I/O performance during bulk crawl insertions.
- `cache_size = -64000`: Allocates 64MB of in-memory page cache per connection.
- `temp_store = MEMORY`: Stores temporary tables and indices in RAM.

---

## 3. Relational Schema Architecture

```
                 ┌───────────────┐
                 │    audits     │
                 └───────┬───────┘
                         │ 1:N
       ┌─────────────────┼─────────────────┬─────────────────┐
       ▼                 ▼                 ▼                 ▼
 ┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
 │   pages   │     │   links   │     │  images   │     │  issues   │
 └─────┬─────┘     └───────────┘     └───────────┘     └───────────┘
       │ 1:N
 ┌─────┴───────────────┐
 ▼                     ▼
[structured_data]   [page_issues]
```

### 3.1 Table: `audits`
Tracks individual crawl jobs and top-level site configuration.
- `id` (TEXT, PK): UUID identifier.
- `domain` (TEXT): Root domain under audit.
- `url` (TEXT): Start/seed URL.
- `status` (TEXT): `pending`, `running`, `complete`, or `stopped`.
- `config_json` (TEXT): Serialized crawl settings (max pages, concurrency, delay).
- `started_at` (TEXT): ISO 8601 initiation timestamp.
- `completed_at` (TEXT): ISO 8601 completion timestamp.

### 3.2 Table: `pages`
Stores individual crawled documents and on-page technical attributes.
- `id` (INTEGER, PK): Auto-incrementing identifier.
- `audit_id` (TEXT, FK -> audits.id): Owning audit reference.
- `url` (TEXT): Full canonicalized document URL.
- `status_code` (INTEGER): HTTP status code.
- `content_type` (TEXT): Raw Content-Type header.
- `title` (TEXT): Page title tag content.
- `meta_description` (TEXT): Meta description tag content.
- `h1` (TEXT): Primary H1 tag content.
- `h2_list` (TEXT): JSON array of H2 heading strings.
- `h3_list` (TEXT): JSON array of H3 heading strings.
- `canonical_url` (TEXT): Canonical link element URL.
- `robots_meta` (TEXT): Meta robots directive string.
- `word_count` (INTEGER): Visible document word count.
- `html_size` (INTEGER): Raw HTML size in bytes.
- `response_time_ms` (INTEGER): Time to first byte in milliseconds.
- `crawl_depth` (INTEGER): Discovery hop depth from seed URL.
- `parent_url` (TEXT): Source page that linked to this document.
- `content_hash` (TEXT): MD5 hash of document body.

### 3.3 Table: `links`
Stores directed edges representing internal and external link architectures.
- `id` (INTEGER, PK): Auto-incrementing identifier.
- `audit_id` (TEXT, FK -> audits.id): Owning audit reference.
- `source_page_id` (INTEGER, FK -> pages.id): Originating page ID.
- `source_url` (TEXT): Originating document URL.
- `target_url` (TEXT): Target destination URL.
- `anchor_text` (TEXT): Visible anchor text.
- `is_internal` (BOOLEAN): 1 for same-domain links, 0 for external links.
- `nofollow` (BOOLEAN): 1 if `rel` contains `nofollow`.

### 3.4 Table: `images`
Tracks all discovered media assets.
- `id` (INTEGER, PK): Auto-incrementing identifier.
- `audit_id` (TEXT, FK -> audits.id): Owning audit reference.
- `page_id` (INTEGER, FK -> pages.id): Declaring page ID.
- `src` (TEXT): Resolved image source URL.
- `alt_text` (TEXT): Alternative text description.
- `width` (INTEGER): Dimensional width in pixels.
- `height` (INTEGER): Dimensional height in pixels.
- `file_size` (INTEGER): File size in bytes.
- `is_lazy_loaded` (BOOLEAN): 1 if `loading="lazy"` is present.

### 3.5 Table: `issues`
Stores detected technical audit issues.
- `id` (INTEGER, PK): Auto-incrementing identifier.
- `audit_id` (TEXT, FK -> audits.id): Owning audit reference.
- `page_id` (INTEGER, FK -> pages.id): Affected page ID.
- `url` (TEXT): Affected URL.
- `category` (TEXT): Technical category (e.g. `indexability`, `onpage`, `links`, `images`).
- `severity` (TEXT): `critical`, `high`, `medium`, or `low`.
- `issue_type` (TEXT): Snake_case identifier (e.g. `missing_h1`, `broken_link`).
- `message` (TEXT): Diagnostic description.
- `recommendation` (TEXT): Actionable remediation instructions.

---

## 4. Batch Insertion Strategies

To maintain maximum crawl throughput, links, images, and issues are inserted using parameterized bulk statements (`executemany`):
- `add_links_batch(links_list)`: Executes parameterized multi-row insert.
- `add_issues_batch(issues_list)`: Batch commits diagnosed anomalies per page.
