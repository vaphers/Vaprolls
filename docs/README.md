# Vaprolls Technical Documentation Suite

This directory contains the detailed technical specifications, architectural references, and implementation guides for the Vaprolls SEO Spider application.

---

## Documentation Index

| Document | Scope & Focus Areas | Primary Code References |
| :--- | :--- | :--- |
| [System Overview](FUNCTIONING.md) | High-level system architecture, operational workflow, and subsystem map | `main.py`, `config.py` |
| [Crawler Engine](crawler_engine.md) | Asynchronous task scheduling, queue management, robots.txt, and sitemaps | `crawler/engine.py`, `crawler/robots.py` |
| [Analysis Pipeline](analysis_pipeline.md) | DOM parsing, link graph traversal, image auditing, CWV, and schema validation | `analyzers/*.py` |
| [URL Dataset Specification](url_dataset_specification.md) | The 11 master columns, asset mapping (CDN, CSS, JS), and regex filtering | `web/app.py` (`enrich_pages_master`) |
| [Database Architecture](database_architecture.md) | SQLite WAL configuration, table schemas, relationships, and queries | `database/db.py`, `database/models.py` |
| [Frontend Workspace](frontend_workspace.md) | Zero-gap SPA layout, draggable panel splitters, and inspector panels | `web/templates/pages.html`, `web/templates/base.html` |
| [API & WebSocket Protocol](api_and_websocket.md) | REST endpoints, WebSocket telemetry frames, and lifespan shutdown handlers | `web/app.py` |
| [Visual Design Style Guide](visual_design_style_guide.md) | Color tokens, typography standards, spacing rules, and CSS specifications | `web/static/css/style.css` |

---

## Cross-Module Architecture Flow

```
[Target URL Input]
       │
       ▼
[Crawler Engine] (docs/crawler_engine.md)
       │
       ├─► [Analysis Pipeline] (docs/analysis_pipeline.md)
       │         │
       │         ▼
       ├─► [Database Layer] (docs/database_architecture.md)
       │         │
       │         ▼
       └─► [API & WebSocket Telemetry] (docs/api_and_websocket.md)
                 │
                 ▼
     [Frontend Workspace] (docs/frontend_workspace.md)
       │
       ▼
     [Master URL Dataset] (docs/url_dataset_specification.md)
```

---

## Reading Guide by Engineering Role

- **Backend & Crawler Engineers**: Start with [Crawler Engine](crawler_engine.md), followed by [Database Architecture](database_architecture.md) and [Analysis Pipeline](analysis_pipeline.md).
- **Frontend & UI Engineers**: Refer to [Frontend Workspace](frontend_workspace.md), [Visual Design Style Guide](visual_design_style_guide.md), and [API & WebSocket Protocol](api_and_websocket.md).
- **Data & SEO Specialists**: Focus on [URL Dataset Specification](url_dataset_specification.md) and [Analysis Pipeline](analysis_pipeline.md).
