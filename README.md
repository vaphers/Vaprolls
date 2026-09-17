# Vaprolls SEO Spider

Vaprolls is an offline-first technical SEO spider and website auditing workspace built in Python. It crawls websites, maps discovered internal and external assets, evaluates on-page ranking factors, and surfaces technical issues through an interactive, multi-tab desktop-style interface or headless command line.

The tool stores all crawl data in a local SQLite database using Write-Ahead Logging (WAL), allowing large crawls to run efficiently without cloud subscriptions or third-party data transmission.

---

## Core Capabilities

- High-throughput asynchronous crawling powered by Python asyncio and httpx, with configurable worker pools and per-request politeness delays.
- Support for multiple crawl scopes: standard recursive spidering, fixed URL list audits, and XML sitemap ingestion.
- Subdomain and cross-domain traversal controls, with URL inclusion and exclusion via regular expressions.
- Headless browser rendering via Playwright to evaluate single-page applications, compare raw HTML against rendered DOMs, and capture console errors.
- 20 specialized analyzers covering status codes, indexability, canonical chains, headings, content readability, keyword prominence, internal PageRank equity, Core Web Vitals, social tags, security headers, mixed content, WCAG accessibility, and internationalization (hreflang).
- Interactive web dashboard featuring 22 categorized data tabs, draggable panel splitters, real-time WebSocket progress telemetry, and page-specific inspection drawers.
- Comprehensive reporting with exports to standalone HTML, formatted Microsoft Excel workbooks, Microsoft Word executive summaries, JSON, and CSV.
- Automated crawl scheduling and regression detection to catch newly introduced 4xx/5xx errors, lost pages, or canonical shifts across deployments.
- Optional AI enhancement via Google Gemini for synthesized executive summaries and prioritized technical remediation plans.

---

## System Requirements

- Python 3.10, 3.11, or 3.12
- Operating System: Windows 10/11, macOS Monterey or newer, or modern Linux distributions (Ubuntu 20.04+, Debian 11+)
- Recommended: Chromium (installed automatically via Playwright if JavaScript rendering is enabled)

---

## Setup and Installation

### 1. Clone the Repository
```bash
git clone https://github.com/vaphers/Vaprolls.git
cd Vaprolls
```

### 2. Create and Activate a Virtual Environment

On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

On Windows (Command Prompt):
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

On Linux or macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you plan to use dynamic JavaScript rendering or automated screenshot generation, install the Playwright browser binaries:
```bash
playwright install chromium
```

### 4. Optional Environment Setup
If you want to use the AI-assisted executive summaries and recommendation prioritizer, set your Gemini API key:

On Windows (PowerShell):
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
```

On Linux or macOS:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

---

## Usage

### Web Workspace
To launch the local web server and open the workspace in your browser:
```bash
python main.py
```
By default, the server starts at `http://localhost:8000/` and attempts to open your default browser automatically.

To run the server on a custom port or interface:
```bash
uvicorn web.app:app --host 127.0.0.1 --port 8080 --reload
```

### Command Line Interface (CLI)
You can run automated crawl jobs and generate reports directly from the terminal without starting the web dashboard:

#### Start a crawl
```bash
python main.py audit https://example.com/ --max-pages 500 --concurrency 15
```

#### Emulate Googlebot or mobile devices
```bash
python main.py audit https://example.com/ --user-agent googlebot_smartphone --max-pages 200
```

#### Render JavaScript with Playwright
```bash
python main.py audit https://example.com/ --js-render --max-pages 100
```

#### List prior audits
```bash
python main.py list
```

#### Generate a report for an existing audit
```bash
python main.py report <AUDIT_ID> --format html
python main.py report <AUDIT_ID> --format xlsx
python main.py report <AUDIT_ID> --format docx
```

#### Compare two audits for regressions
```bash
python main.py compare <BASELINE_AUDIT_ID> <NEW_AUDIT_ID>
```

---

## Configuration Reference

Default settings are defined in `config.py`. Common parameters include:

| Setting | Default | Description |
| :--- | :--- | :--- |
| `CRAWL_CONCURRENCY` | `15` | Maximum number of simultaneous worker requests |
| `CRAWL_DELAY` | `0.0` | Throttling delay between requests in seconds |
| `MAX_PAGES` | `5000` | Safety limit on pages crawled per job (set to 0 for unlimited) |
| `REQUEST_TIMEOUT` | `10` | HTTP timeout per request in seconds |
| `DB_PATH` | `data/audits.db` | Path to the SQLite database file |
| `USER_AGENT` | Chrome Desktop | Default HTTP User-Agent string |
| `RESPECT_ROBOTS_TXT` | `True` | Whether to honor robots.txt exclusion rules |
| `FOLLOW_REDIRECTS` | `True` | Whether to follow HTTP 3xx redirect locations |
| `MAX_REDIRECT_CHAIN` | `10` | Maximum redirect hops before flagging a loop |
| `CRAWL_SUBDOMAINS` | `False` | Whether to crawl discovered subdomains of the root host |
| `JS_RENDER_ENABLED` | `False` | Whether to render pages in headless Chromium |

---

## Architecture Overview

The system is organized into modular layers:

```
[Target URL]
     │
     ▼
[Crawl Engine] (crawler/engine.py, robots.py, sitemap.py)
     │
     ├─► [Analysis Pipeline] (analyzers/*.py - 20 specialized auditors)
     │         │
     │         ▼
     ├─► [Database Layer] (database/db.py, models.py - 18 tables, SQLite WAL)
     │         │
     │         ├─► [Reports & Exports Engine] (reports/*.py - HTML, Excel, Word, JSON, CSV)
     │         ├─► [AI Enhancements] (ai/gemini_enhancer.py - Google Gemini)
     │         ├─► [Scheduler & Regressions] (scheduler.py)
     │         │
     │         ▼
     └─► [API & WebSocket Telemetry] (web/app.py)
               │
               ▼
   [Frontend Workspace] (web/templates/pages.html, web/enrichment.py - 22 tabs)
```

---

## Detailed Documentation Suite

For detailed technical specifications, database schemas, and implementation guides, refer to the documentation in the `docs/` directory:

- [Documentation Index](docs/README.md): Complete guide directory and reading tracks.
- [System Overview](docs/FUNCTIONING.md): End-to-end processing pipeline and component breakdown.
- [Crawler Engine](docs/crawler_engine.md): Queue management, crawl modes, Playwright rendering, and robot exclusion.
- [Analysis Pipeline](docs/analysis_pipeline.md): Comprehensive catalog of all 20 analyzers, rules, and scoring logic.
- [URL Dataset Specification](docs/url_dataset_specification.md): The 22 workspace tabs, 11 master columns, and asset inference rules.
- [Database Architecture](docs/database_architecture.md): SQLite WAL configuration and complete 18-table relational schema.
- [Frontend Workspace](docs/frontend_workspace.md): Dense SPA geometry, draggable panels, and inspector mechanics.
- [API & WebSocket Protocol](docs/api_and_websocket.md): REST endpoints, WebSocket telemetry frames, and shutdown lifecycle.
- [CLI & Scheduler Guide](docs/cli_and_scheduler.md): Command line flags, automated crawl scheduling, and regression alerting.
- [Reporting & Exports Guide](docs/reporting_and_exports.md): Multi-format report generation, SEOptimer replica, and comparative diffing.
- [AI Enhancements](docs/ai_enhancements.md): Google Gemini setup, executive summary synthesis, and prioritization.
- [Visual Design Style Guide](docs/visual_design_style_guide.md): Design tokens, typography, and UI rules.

---

## License

Internal Enterprise Technical Tool. All rights reserved.
