# API & WebSocket Telemetry Protocol

## 1. Module Overview

The HTTP routing and WebSocket telemetry interfaces are implemented in `web/app.py` using FastAPI. They provide real-time control over crawl jobs, telemetry streaming, relational data inspection, and CSV export capabilities.

Related documentation:
- Ingestion engine: [Crawler Engine](crawler_engine.md)
- Dataset structure: [URL Dataset Specification](url_dataset_specification.md)
- Workspace consumption: [Frontend Workspace](frontend_workspace.md)

---

## 2. REST API Endpoints

### 2.1 Start Crawl Job
Initiates an asynchronous crawl job in the background.

- **Endpoint**: `POST /api/audit/start`
- **Request Body (JSON)**:
  ```json
  {
    "url": "https://example.com/",
    "max_pages": 500,
    "concurrency": 15,
    "crawl_delay": 0.0,
    "mode": "spider"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "audit_id": "9b9c5767-026d-4978-a62a-13502e3a5b50",
    "status": "started"
  }
  ```

### 2.2 Stop Crawl Job
Aborts active workers for an in-flight crawl job and sets its database status to `stopped`.

- **Endpoint**: `POST /api/audit/{audit_id}/stop`
- **Response (200 OK)**:
  ```json
  {
    "status": "stopped",
    "audit_id": "9b9c5767-026d-4978-a62a-13502e3a5b50"
  }
  ```

### 2.3 Page & Asset Inspector
Returns full relational and on-page attributes for a specific item. Supports both crawled page IDs (`< 100000`) and virtual asset IDs (`>= 100000`).

- **Endpoint**: `GET /api/audit/{audit_id}/page/{page_id}/inspector`
- **Response Structure (200 OK)**:
  ```json
  {
    "page": {
      "id": 1381,
      "url": "https://example.com/",
      "status_code": 200,
      "status": "OK",
      "indexability": "Indexable",
      "indexability_status": "OK",
      "content_type": "text/html; charset=utf-8",
      "title": "Page Title",
      "meta_description": "Meta description text...",
      "h1": "Heading 1",
      "canonical_url": "https://example.com/",
      "length": 241430,
      "word_count": 850
    },
    "inlinks": [
      {
        "source_url": "https://example.com/blog",
        "anchor_text": "Home",
        "status_code": 200,
        "nofollow": false
      }
    ],
    "outlinks": [
      {
        "target_url": "https://example.com/about",
        "anchor_text": "About Us",
        "is_internal": true,
        "nofollow": false
      }
    ],
    "images": [
      {
        "src": "https://example.com/logo.png",
        "alt_text": "Company Logo",
        "width": 200,
        "height": 50,
        "file_size": 4096,
        "is_lazy_loaded": true
      }
    ],
    "structured_data": [
      {
        "schema_type": "Organization",
        "data_json": "{...}",
        "is_valid": true
      }
    ],
    "issues": [
      {
        "severity": "medium",
        "issue_type": "missing_h1",
        "message": "Page is missing a top-level H1 heading.",
        "recommendation": "Add a descriptive H1 heading."
      }
    ],
    "headers": {
      "server": "cloudflare",
      "content-type": "text/html; charset=utf-8"
    },
    "serp": {
      "title": "Page Title",
      "url": "https://example.com/",
      "description": "Meta description text..."
    }
  }
  ```

### 2.4 Export Filtered Dataset to CSV
Streams the active filtered URL dataset as a formatted CSV file.

- **Endpoint**: `GET /api/audit/{audit_id}/export/urls.csv`
- **Query Parameters**: `tab`, `status`, `indexable`, `content_type`, `include`, `exclude`, `q`.
- **Response**: `text/csv` attachment with all 11 master columns.

---

## 3. WebSocket Real-Time Progress Protocol

- **Connection URL**: `ws://<HOST>/ws/audit/{audit_id}`
- **Message Direction**: Server to Client.
- **Message Payload (JSON)**:
  ```json
  {
    "type": "progress",
    "crawled": 45,
    "total": 120,
    "url": "https://example.com/collections/catalog"
  }
  ```
- **Client Handling**: The client calculates `pct = Math.round((crawled / total) * 100)` and updates `#spider-progress-bar` and `#spider-progress-nums`.
- **Completion**: When the WebSocket closes, the frontend automatically refreshes to display all newly crawled URLs.

---

## 4. Lifespan and Graceful Shutdown Management

FastAPI's `@asynccontextmanager` controls the server lifecycle:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup initialization
    yield
    # Shutdown sequence
    for aid, task in list(active_audits.items()):
        if not task.done():
            task.cancel()
    for aid, conns in list(ws_connections.items()):
        for ws in conns:
            await ws.close(code=1001, reason="Server shutting down")
```
- Active crawl coroutines are cleanly canceled without leaving dangling threads.
- WebSocket clients receive an explicit `1001` disconnect code.
- Database locks and WAL checkpoint transactions are cleanly committed.
