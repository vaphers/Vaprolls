# CLI & Scheduler Guide

## 1. Module Overview

Vaprolls includes a fully featured Command Line Interface (CLI) in `cli.py` and an automated recurring crawl and regression alerting engine in `scheduler.py`.

These tools enable automated headless audits, CI/CD pipeline integration, recurring regression testing, and terminal-based report generation without launching the web dashboard.

Related documentation:
- Crawl engine settings: [Crawler Engine](crawler_engine.md)
- Storage schema: [Database Architecture](database_architecture.md)
- Report exports: [Reporting & Exports Guide](reporting_and_exports.md)

---

## 2. Command Line Interface (`cli.py`)

The CLI is invoked via `main.py` using subcommand syntax:
```bash
python main.py [subcommand] [arguments]
```

### 2.1 Subcommand: `audit`
Executes an immediate crawl and analysis pipeline against a target URL.

```bash
python main.py audit <URL> [options]
```

#### Available Options:
- `--max-pages <int>`: Maximum number of pages to crawl (default: 500). Set to 0 for unlimited.
- `--concurrency <int>`: Number of simultaneous asynchronous worker tasks (default: 15).
- `--delay <float>`: Throttle delay between HTTP requests in seconds (default: 0.0).
- `--mode <str>`: Crawl mode (`spider`, `list`, or `sitemap`). Default is `spider`.
- `--include <regex>`: Regex pattern; only matching URLs are crawled.
- `--exclude <regex>`: Regex pattern; matching URLs are excluded.
- `--user-agent <str>`: Preset User-Agent name (`default`, `chrome_desktop`, `chrome_mobile`, `googlebot_smartphone`, `googlebot_desktop`, `bingbot`).
- `--basic-auth <user:pass>`: HTTP Basic Authentication credentials.
- `--auth-user <str>` / `--auth-pass <str>`: Explicit HTTP Basic Auth username and password.
- `--proxy <url>`: Outbound HTTP or SOCKS5 proxy URL (e.g. `http://proxy:8080`).
- `--js-render`: Enable Playwright headless browser rendering for client-side JavaScript execution.
- `--no-robots`: Bypass `robots.txt` disallow directives (for testing staging environments).
- `--no-redirects`: Disable automatic HTTP 3xx redirect following.
- `--max-depth <int>`: Maximum crawl depth (click distance from seed URL).
- `--subdomains`: Permit crawling across subdomains of the target domain.
- `--urls-file <path>`: Path to a file containing URLs to crawl (required when `--mode list`).
- `--export-all <dir>`: Automatically export HTML, CSV, JSON, XLSX, and DOCX reports to the specified directory upon completion.
- `--report <format>`: Generate a report immediately following the audit (`html`, `csv`, `json`, `xlsx`, `docx`).

#### Example:
```bash
python main.py audit https://example.com/ --max-pages 250 --concurrency 10 --user-agent googlebot_smartphone --report html
```

---

### 2.2 Subcommand: `list`
Lists all previously executed audits stored in the database.

```bash
python main.py list
```

#### Output:
Displays a tabular summary of all audits, including Audit ID, Root Domain, Start URL, Status, Total Pages Crawled, Discovered Issues, Health Score, and Execution Date.

---

### 2.3 Subcommand: `report`
Generates an exported report for an existing completed audit.

```bash
python main.py report <AUDIT_ID> --format <FORMAT> [--output <DIR>]
```

#### Arguments:
- `<AUDIT_ID>`: UUID of the target audit.
- `--format`: Desired output format: `html`, `json`, `csv`, `xlsx`, `docx`, `seoptimer`.
- `--output` (optional): Destination directory for generated report files (default: `reports_output/`).

---

### 2.4 Subcommand: `compare`
Performs a comparative regression diff between two audit runs.

```bash
python main.py compare <AUDIT_ID_1> <AUDIT_ID_2> [--format <FORMAT>]
```

#### Comparison Metrics Evaluated:
- Overall Health Score delta (improvement vs. degradation).
- Total pages crawled difference.
- New 4xx / 5xx error pages introduced in the newer crawl.
- Removed or 404 pages compared to the prior baseline.
- Title and meta description changes on identical URLs.
- Core Web Vitals latency regressions.
- Changes in internal link equity (PageRank shifts).

---

## 3. Crawl Scheduler & Regression Engine (`scheduler.py`)

The `CrawlScheduler` class in `scheduler.py` automates periodic crawls and regression testing.

### 3.1 Architectural Flow

```
[Scheduled Trigger] (cron / task scheduler)
       │
       ▼
[CrawlScheduler.run_and_compare(url)]
       │
       ├─► 1. Query DB for prior baseline audit (matching domain)
       │
       ├─► 2. Execute fresh crawl & full analyzer pipeline
       │
       ├─► 3. Invoke AuditComparator (diff new audit vs baseline)
       │
       └─► 4. Generate Regression Alert Payload:
             - New 4xx / 5xx errors
             - Dropped / 404 URLs
             - Health score drops (> 5 points)
             - Missing / modified canonicals
             - Response time spikes
```

### 3.2 Regression Detection Criteria

The regression engine flags the following critical conditions:

| Regression Flag | Trigger Condition | Severity |
| :--- | :--- | :--- |
| `health_score_drop` | New audit health score is $\ge 5$ points lower than baseline | Critical |
| `new_broken_pages` | URLs returning 200 in baseline now return 4xx or 5xx | Critical |
| `lost_pages` | URLs present in baseline missing from new crawl | Warning |
| `canonical_regressions` | Pages where canonical URL was altered or removed | Warning |
| `title_regressions` | Significant alteration or removal of title tags | Info |
| `response_time_increase` | Average site latency increased by $\ge 50\%$ | Warning |

### 3.3 Programmatic Usage Example

```python
import asyncio
from database.db import Database
from scheduler import CrawlScheduler
from config import get_config

async def run_nightly_job():
    config = get_config()
    async with Database(config.DB_PATH) as db:
        scheduler = CrawlScheduler(db)
        result = await scheduler.run_and_compare("https://example.com/")
        
        regressions = result.get("regressions", {})
        if regressions.get("has_regressions"):
            print("ALERT: SEO regressions detected!")
            print(f"Health score drop: {regressions.get('score_delta')}")
            print(f"New 4xx errors: {len(regressions.get('new_4xx', []))}")
        else:
            print("Audit passed with no regressions.")

if __name__ == "__main__":
    asyncio.run(run_nightly_job())
```
