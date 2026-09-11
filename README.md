# Vaprolls SEO Spider & URL Explorer

Vaprolls is an enterprise-grade, high-density website crawler and technical SEO workspace. It crawls web applications to extract, index, and analyze on-page SEO factors, link architectures, media assets, HTTP response codes, Core Web Vitals, and structured data in a single-page interactive interface.

---

## Prerequisites

Before installing the application on a new machine, verify that your environment meets the following requirements:

### Operating System
- Windows 10/11, Windows Server 2019+
- macOS 12 (Monterey) or newer
- Linux (Ubuntu 20.04+, Debian 11+, CentOS/RHEL 8+)

### Software Dependencies
- **Python**: Version 3.10, 3.11, or 3.12
- **Git**: Version 2.20 or newer
- **Web Browser**: Modern Chromium-based browser, Firefox, or Safari
- **Optional**: Google Chrome or Chromium (required only if automated full-page visual screenshot generation is enabled)

---

## Installation Guide (New Machine Setup)

Follow these steps to set up and run Vaprolls on a clean system:

### 1. Clone the Repository
Open your terminal or PowerShell and clone the project repository:
```bash
git clone https://github.com/vaphers/Vaprolls.git
cd Vaprolls
```

### 2. Create a Virtual Environment
Isolate project dependencies within a Python virtual environment:

- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(If execution policies prevent activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

- **Windows (Command Prompt)**:
  ```cmd
  python -m venv venv
  venv\Scripts\activate.bat
  ```

- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Upgrade Pip and Install Dependencies
Ensure `pip` is up to date and install all required Python packages:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify Local Directory Structure
Ensure the database and assets directory exists:
```bash
mkdir data
```

---

## Running the Application

### Option A: Launch via Entrypoint Script (Recommended)
Start the web dashboard directly:
```bash
python main.py
```
This initializes the FastAPI backend and automatically opens the dashboard in your default web browser at `http://127.0.0.1:8000/`.

### Option B: Run via Uvicorn CLI
For development or headless servers:
```bash
uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
```

### Option C: Command Line Interface (CLI)
You can run automated crawl jobs and generate static reports without the web interface:

- **Start an audit**:
  ```bash
  python main.py audit https://example.com/ --max-pages 500 --concurrency 15
  ```
- **List previous audits**:
  ```bash
  python main.py list
  ```
- **Generate a report**:
  ```bash
  python main.py report <AUDIT_ID> --format html
  ```
- **Compare two crawls**:
  ```bash
  python main.py compare <AUDIT_ID_1> <AUDIT_ID_2>
  ```

---

## Configuration Reference

Default settings are managed in `config.py`. Core configuration options include:

| Setting | Default | Description |
| :--- | :--- | :--- |
| `CRAWL_CONCURRENCY` | `15` | Maximum number of simultaneous asynchronous worker requests |
| `CRAWL_DELAY` | `0.0` | Artificial throttle delay between requests (in seconds) |
| `MAX_PAGES` | `5000` | Maximum limit of pages to crawl per job |
| `REQUEST_TIMEOUT` | `10` | HTTP network timeout per request in seconds |
| `DB_PATH` | `data/audits.db` | Relative path to the SQLite persistence file |
| `USER_AGENT` | Chrome Desktop | Default User-Agent header emitted by the crawler |
| `RESPECT_ROBOTS_TXT` | `True` | Enforce compliance with target site's `robots.txt` rules |
| `FOLLOW_REDIRECTS` | `True` | Follow HTTP 3xx redirect locations automatically |

---

## Documentation

For an in-depth breakdown of system architecture, data enrichment, the 11-column URL dataset specification, WebSocket streaming, and panel mechanics, refer to:
- [Technical Documentation Index](docs/README.md)
- [System Overview](docs/FUNCTIONING.md)
- [Crawler Engine](docs/crawler_engine.md)
- [Analysis Pipeline](docs/analysis_pipeline.md)
- [URL Dataset Specification (11 Columns)](docs/url_dataset_specification.md)
- [Database Architecture (SQLite WAL)](docs/database_architecture.md)
- [Frontend Workspace & Draggable Panels](docs/frontend_workspace.md)
- [API & WebSocket Telemetry](docs/api_and_websocket.md)
- [Visual Design Style Guide](docs/visual_design_style_guide.md)

---

## License & Support

Internal Enterprise Technical Tool. All rights reserved.
