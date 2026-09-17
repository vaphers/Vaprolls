# Reporting & Exports Guide

## 1. Module Overview

Vaprolls includes a flexible reporting and data export system located in the `reports/` package. It enables generating multi-format audit deliverables for stakeholders, clients, and internal engineering teams.

Related documentation:
- CLI report triggers: [CLI & Scheduler Guide](cli_and_scheduler.md)
- Schema definitions: [Database Architecture](database_architecture.md)
- Telemetry endpoints: [API & WebSocket Protocol](api_and_websocket.md)

---

## 2. Supported Export Formats

The `ReportGenerator` class in `reports/generator.py` generates reports in five distinct formats:

| Format | Extension | Library | Primary Use Case |
| :--- | :--- | :--- | :--- |
| **Interactive HTML** | `.html` | Jinja2 / Native HTML | Standalone, self-contained audit deliverable viewable in any web browser. |
| **Microsoft Excel** | `.xlsx` | `openpyxl` | Formatted multi-tab workbook with colored status indicators for spreadsheet analysis. |
| **Microsoft Word** | `.docx` | `python-docx` | Formatted executive summary document with styled headings and tables for client presentation. |
| **JSON Export** | `.json` | `json` | Complete machine-readable data dump of pages, issues, links, and performance metrics. |
| **CSV Export** | `.csv` | `csv` | Flat table exports of issues, crawl frontiers, and the master URL dataset. |

---

## 3. Executive SEOptimer-Style Report Builder (`reports/seoptimer_builder.py`)

The application features a specialized report builder designed for executive audits and client reviews:

### 3.1 Letter-Grade Evaluation
The builder calculates categorical letter grades (A+, A, B, C, D, F) across five core domains:
1. **On-Page SEO**: Title tags, meta descriptions, heading structures, body copy depth, image alt tags, canonicals, and keyword consistency.
2. **Links & Authority**: Internal link structure, PageRank equity distribution, external outbound link health, and broken link counts.
3. **Usability & Mobile**: Viewport configuration, mobile alternate links, font sizing, and touch target feasibility.
4. **Performance & Speed**: HTML payload size, DOM node count, compression (gzip/brotli), server response time, and Web Vitals metrics.
5. **Security & Protocol**: HTTPS adoption, SSL/TLS configuration, HSTS, Content Security Policy, and security headers.

### 3.2 Visual Speed & Object Breakdown
Inspects and categorizes all page objects (HTML documents, JavaScript bundles, CSS stylesheets, web fonts, and images):
- Calculates total byte weights and request counts per category.
- Flags render-blocking assets.
- Provides actionable recommendations for payload reduction.

---

## 4. Comparative Audit Diffing (`reports/comparator.py`)

The `AuditComparator` module evaluates two separate audit runs (a baseline audit and a subsequent audit) to detect structural improvements or technical regressions:

```
[Baseline Audit: ID A] ──────┐
                              ├─► [AuditComparator.compare(id_a, id_b)]
[Subsequent Audit: ID B] ────┘                    │
                                                  ▼
                                      [Comparative Diff Report]
                                      ├─ Health Score Delta
                                      ├─ Page Count Delta
                                      ├─ New 4xx / 5xx Errors
                                      ├─ Resolved Issues
                                      ├─ Regressed Pages
                                      └─ Internal PageRank Shifts
```

### 4.1 Comparative Metrics
- **New URLs Discovered**: URLs present in Audit B that did not exist in Audit A.
- **Removed / Missing URLs**: URLs present in Audit A missing from Audit B.
- **Status Code Changes**: e.g., 200 OK pages that degraded to 404 or 500.
- **Title / Meta Modifications**: Content alterations on existing pages.
- **Fixed Issues**: Diagnostic issues detected in Audit A that are no longer present in Audit B.
- **New Issues**: Newly introduced problems flagged in Audit B.

---

## 5. Generating Reports via CLI and Code

### 5.1 CLI Execution
```bash
# Generate standalone HTML report
python main.py report <AUDIT_ID> --format html

# Generate Excel workbook
python main.py report <AUDIT_ID> --format xlsx

# Generate Word document
python main.py report <AUDIT_ID> --format docx

# Generate all formats simultaneously
python main.py audit https://example.com/ --export-all ./deliverables/
```

### 5.2 Python API Usage

```python
import asyncio
from database.db import Database
from reports.generator import ReportGenerator

async def export_audit(audit_id: str):
    async with Database("data/audits.db") as db:
        generator = ReportGenerator(db, audit_id, output_dir="reports_output")
        
        html_file = await generator.generate_html()
        excel_file = await generator.generate_excel()
        docx_file = await generator.generate_docx()
        json_file = await generator.generate_json()
        
        print(f"Generated deliverables in reports_output/")

if __name__ == "__main__":
    asyncio.run(export_audit("your-audit-id"))
```
