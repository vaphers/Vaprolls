# API & WebSocket Telemetry Protocol

## 1. Module Overview

The HTTP routing and WebSocket telemetry interfaces are implemented in `web/app.py` using FastAPI. They provide real-time control over crawl jobs, live telemetry streaming, tabular data inspection, right sidebar panel aggregations, and multi-format data exports.

Related documentation:
- Ingestion engine: [Crawler Engine](crawler_engine.md)
- Dataset structure: [URL Dataset Specification](url_dataset_specification.md)
- Workspace interface: [Frontend Workspace](frontend_workspace.md)
- Reports and exports: [Reporting & Exports Guide](reporting_and_exports.md)

---

## 2. REST API Endpoints

### 2.1 Audit Lifecycle Control

#### Start Crawl Job
Initiates an asynchronous crawl job in the background.
- **Endpoint**: `POST /api/audit/start`
- **Request Body (JSON)**:
  ```json
  {
    "url": "https://example.com/",
    "max_pages": 500,
    "concurrency": 15,
    "crawl_delay": 0.0,
    "mode": "spider",
    "include_regex": "^https://example\\.com/blog/",
    "exclude_regex": "\\.pdf$",
    "user_agent_preset": "default",
    "basic_auth": null,
    "urls_text": null
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "audit_id": "9b9c5767-026d-4978-a62a-13502e3a5b50",
    "status": "started"
  }
  ```

#### Stop Crawl Job
Aborts active workers for an in-flight crawl job and sets database status to `stopped`.
- **Endpoint**: `POST /api/audit/{audit_id}/stop`
- **Response (200 OK)**:
  ```json
  {
    "status": "stopped",
    "audit_id": "9b9c5767-026d-4978-a62a-13502e3a5b50"
  }
  ```

#### Clear Audits
Wipes active audits and in-memory caches.
- **Endpoint**: `POST /api/audit/clear`
- **Response (200 OK)**:
  ```json
  {
    "status": "cleared"
  }
  ```

#### Check Audit Status
Returns current status and aggregate metrics for an audit.
- **Endpoint**: `GET /api/audit/{audit_id}/status`
- **Response (200 OK)**:
  ```json
  {
    "audit_id": "9b9c5767-026d-4978-a62a-13502e3a5b50",
    "status": "complete",
    "total_pages": 342,
    "health_score": 92.5,
    "started_at": "2026-09-17T12:00:00",
    "completed_at": "2026-09-17T12:03:45"
  }
  ```

---

### 2.2 Tabular Data & Inspector Endpoints

#### Get Audit Tab Data
Returns paginated, sorted, and filtered records for any of the 22 workspace tabs.
- **Endpoint**: `GET /api/audit/{audit_id}/tab/{tab_key}`
- **Query Parameters**:
  - `tab_key` (path): `all`, `internal`, `external`, `response_codes`, `page_titles`, `meta_description`, `h1`, `h2`, `content`, `images`, `canonicals`, `pagination`, `directives`, `hreflang`, `javascript`, `links`, `security`, `structured_data`, `sitemaps`, `accessibility`, `custom_search`.
  - `page` (int, default: 1): Page number.
  - `page_size` (int, default: 50000): Number of rows per page.
  - `sort_by` (str, optional): Column key to sort by (e.g. `url`, `status_code`, `internal_pagerank`).
  - `sort_dir` (str, default: `asc`): Sort direction (`asc` or `desc`).
  - `include` (str, optional): Regex or substring filter.
  - `exclude` (str, optional): Exclusion regex.
- **Response (200 OK)**:
  ```json
  {
    "tab": "internal",
    "columns": [ ... ],
    "dynamic_columns": [ ... ],
    "rows": [ ... ],
    "total": 342,
    "page": 1,
    "page_size": 500
  }
  ```

#### Page Inspector Data
Returns detailed relational data for the bottom split inspector panel.
- **Endpoint**: `GET /api/audit/{audit_id}/page/{page_id}/inspector`
- **Response Structure (200 OK)**:
  ```json
  {
    "page": {
      "id": 1381,
      "url": "https://example.com/blog/article",
      "status_code": 200,
      "title": "Article Title",
      "meta_description": "Article summary...",
      "h1": "Article Title",
      "canonical_url": "https://example.com/blog/article",
      "internal_pagerank": 64.2,
      "word_count": 1250,
      "response_time_ms": 142.5
    },
    "inlinks": [
      { "source_url": "https://example.com/", "anchor_text": "Read Article", "rel": "" }
    ],
    "outlinks": [
      { "target_url": "https://example.com/about", "anchor_text": "About Us", "is_internal": true }
    ],
    "images": [
      { "src": "https://example.com/hero.webp", "alt_text": "Hero banner", "has_dimensions": true }
    ],
    "serp": {
      "title": "Article Title",
      "meta_description": "Article summary...",
      "url": "https://example.com/blog/article"
    },
    "headers": {
      "content-type": "text/html; charset=utf-8",
      "strict-transport-security": "max-age=31536000; includeSubDomains"
    },
    "structured_data": [
      { "schema_type": "Article", "format": "json-ld", "is_valid": true }
    ],
    "issues": [ ... ]
  }
  ```

---

### 2.3 Right Sidebar Aggregation Endpoints

#### Issues Summary
Returns diagnostic issues grouped by category and severity.
- **Endpoint**: `GET /api/audit/{audit_id}/right-panel/issues`
- **Response (200 OK)**:
  ```json
  {
    "critical": [ ... ],
    "warning": [ ... ],
    "info": [ ... ],
    "counts": { "critical": 3, "warning": 12, "info": 24 }
  }
  ```

#### Site Structure Tree
Returns hierarchical folder and path distribution of the crawled site.
- **Endpoint**: `GET /api/audit/{audit_id}/right-panel/site-structure`
- **Response (200 OK)**: Nested tree representing directories, file counts, and status breakdowns.

#### Response Times Distribution
Returns server latency distributed across 5 standard performance buckets:
- **Endpoint**: `GET /api/audit/{audit_id}/right-panel/response-times`
- **Buckets**: `0-200ms`, `200-500ms`, `500-1000ms`, `1-2s`, `>2s`.

#### Crawl Depth Distribution
Returns page count grouped by click distance from seed URL:
- **Endpoint**: `GET /api/audit/{audit_id}/right-panel/depth`
- **Distribution**: Depth 0 (seed), Depth 1, Depth 2, Depth 3, Depth 4+.

#### Segments Summary
Returns distribution of pages across primary top-level directory segments:
- **Endpoint**: `GET /api/audit/{audit_id}/right-panel/segments`

---

### 2.4 Export & Utility Endpoints

#### Export Master URLs CSV
Generates a downloadable CSV export of the master URL dataset:
- **Endpoint**: `GET /api/audit/{audit_id}/export/urls.csv`
- **Headers**: `Content-Disposition: attachment; filename="vaprolls_urls_<audit_id>.csv"`

#### Multi-Format Export
Generates audit exports in various file formats:
- **Endpoint**: `GET /api/audit/{audit_id}/export/{format}`
- **Supported Formats**: `html`, `json`, `csv`, `xlsx`, `docx`, `seoptimer`.

#### Mobile Preview Proxy
Proxies requested URLs in an iframe to simulate mobile viewport rendering:
- **Endpoint**: `GET /api/proxy/mobile-preview?url={target_url}`

---

## 3. WebSocket Real-Time Telemetry Protocol

Live crawl telemetry streams over WebSocket to keep the user interface updated during active crawling without client polling.

- **Connection URL**: `ws://localhost:8000/ws/audit/{audit_id}`
- **Protocol**: Standard WebSocket (JSON text frames).

### 3.1 Server-to-Client Frame Types

#### Progress Frame (`type: "progress"`)
Emitted as pages are crawled and queued:
```json
{
  "type": "progress",
  "status": "crawling",
  "crawled": 42,
  "total": 128,
  "url": "https://example.com/pricing"
}
```

#### Status Transition Frame (`type: "status"`)
Emitted when transitioning between crawl phases (e.g. from crawling to post-crawl analysis):
```json
{
  "type": "status",
  "status": "analyzing",
  "crawled": 128,
  "total": 128,
  "url": ""
}
```

#### Completion Frame (`type: "complete"`)
Emitted when all workers, analyzers, and database commits have completed:
```json
{
  "type": "complete",
  "audit_id": "9b9c5767-026d-4978-a62a-13502e3a5b50"
}
```
Following the completion frame, the WebSocket connection closes cleanly with code `1000` (Normal Closure).

---

## 4. Server Lifespan & Connection Cleanup

The application implements FastAPI's `lifespan` context manager in `web/app.py`:
- **Active Task Cancellation**: If the server terminates while crawls are running, in-flight crawler tasks in `active_audits` are cleanly canceled.
- **WebSocket Closure**: Open WebSocket connections receive code `1001` (Going Away) before terminating.
- **Cache Eviction**: In-memory page headers, raw HTML, and technology caches are cleared on shutdown.
