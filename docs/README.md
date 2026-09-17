# Vaprolls Technical Documentation Suite

This directory contains technical specifications, architectural references, and implementation guides for the Vaprolls SEO Spider application.

---

## Documentation Index

| Document | Scope & Focus Areas | Primary Code References |
| :--- | :--- | :--- |
| [System Overview](FUNCTIONING.md) | High-level system architecture, operational workflow, and subsystem map | `main.py`, `config.py` |
| [Crawler Engine](crawler_engine.md) | Asynchronous task scheduling, queue management, robots.txt, and sitemaps | `crawler/engine.py`, `crawler/robots.py` |
| [Analysis Pipeline](analysis_pipeline.md) | The 20 specialized analyzers, audit rules, scoring formulas, and issue classification | `analyzers/*.py` |
| [URL Dataset Specification](url_dataset_specification.md) | The 22 primary tabs, 11 master columns, asset mapping (CDN, CSS, JS), and regex filtering | `web/enrichment.py`, `web/app.py` |
| [Database Architecture](database_architecture.md) | SQLite WAL configuration, 18 relational table schemas, and queries | `database/db.py`, `database/models.py` |
| [Frontend Workspace](frontend_workspace.md) | Zero-gap SPA layout, draggable panel splitters, and inspector sub-tabs | `web/templates/pages.html`, `web/templates/base.html` |
| [API & WebSocket Protocol](api_and_websocket.md) | REST endpoints, WebSocket telemetry frames, right-panel aggregations, and lifespan handlers | `web/app.py` |
| [CLI & Scheduler Guide](cli_and_scheduler.md) | Headless audit execution, CLI options, recurring crawls, and regression detection engine | `cli.py`, `scheduler.py` |
| [Reporting & Exports Guide](reporting_and_exports.md) | Multi-format deliverables (HTML, XLSX, DOCX, JSON, CSV), SEOptimer builder, and audit diffing | `reports/*.py` |
| [AI Enhancements](ai_enhancements.md) | Google Gemini integration, executive summary generation, fix priorities, and intent classification | `ai/gemini_enhancer.py` |
| [Visual Design Style Guide](visual_design_style_guide.md) | Color tokens, typography standards, spacing rules, and CSS specifications | `web/static/css/style.css` |

---

## Cross-Module Architecture Flow

```
[Target URL Input]
       │
       ▼
[Crawler Engine] (docs/crawler_engine.md)
       │
       ├─► [Analysis Pipeline - 20 Analyzers] (docs/analysis_pipeline.md)
       │         │
       │         ▼
       ├─► [Database Layer - 18 Tables] (docs/database_architecture.md)
       │         │
       │         ├─► [Reports & Exports Engine] (docs/reporting_and_exports.md)
       │         │
       │         ├─► [AI Gemini Enhancements] (docs/ai_enhancements.md)
       │         │
       │         ▼
       └─► [API & WebSocket Telemetry] (docs/api_and_websocket.md)
                 │
                 ▼
     [Frontend Workspace] (docs/frontend_workspace.md)
       │
       ▼
     [Master URL Dataset - 22 Tabs] (docs/url_dataset_specification.md)
```

---

## Reading Guide by Engineering Role

- **Backend & Crawler Engineers**: Start with [Crawler Engine](crawler_engine.md), followed by [Database Architecture](database_architecture.md), [Analysis Pipeline](analysis_pipeline.md), and [CLI & Scheduler Guide](cli_and_scheduler.md).
- **Frontend & UI Engineers**: Refer to [Frontend Workspace](frontend_workspace.md), [Visual Design Style Guide](visual_design_style_guide.md), and [API & WebSocket Protocol](api_and_websocket.md).
- **Data & SEO Specialists**: Focus on [URL Dataset Specification](url_dataset_specification.md), [Analysis Pipeline](analysis_pipeline.md), [Reporting & Exports Guide](reporting_and_exports.md), and [AI Enhancements](ai_enhancements.md).
- **DevOps & Automation Engineers**: Focus on [CLI & Scheduler Guide](cli_and_scheduler.md) and [System Overview](FUNCTIONING.md).
