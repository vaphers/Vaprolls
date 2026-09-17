# Crawler Engine Specification

## 1. Module Overview

The crawler subsystem resides in `crawler/engine.py` and is responsible for autonomously discovering, fetching, and queuing resources from target web properties. It operates asynchronously using Python `asyncio` and `httpx`, enforcing network politeness and robot exclusion rules while maintaining high request concurrency.

Related documentation:
- Data storage: [Database Architecture](database_architecture.md)
- Post-fetch extraction: [Analysis Pipeline](analysis_pipeline.md)
- Telemetry dispatch: [API & WebSocket Protocol](api_and_websocket.md)
- CLI and scheduling: [CLI & Scheduler Guide](cli_and_scheduler.md)

---

## 2. Queue Management and Worker Architecture

### 2.1 Asynchronous Worker Pool
The crawler instantiates a pool of concurrent coroutine workers driven by `asyncio.Queue`:

```
                    ┌─────────────────────────┐
                    │      asyncio.Queue      │
                    │   (Discovered URLs)     │
                    └────────────┬────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
     [Worker 1]            [Worker 2]            [Worker N]
  (HTTP Fetcher)        (HTTP Fetcher)        (HTTP Fetcher)
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 ▼
                     [Response Dispatcher]
                                 │
                     [Database / Pipeline]
```

- **Concurrency Control**: Defaults to `15` concurrent workers, configured via `Config.CRAWL_CONCURRENCY` in `config.py` or overridden per audit request.
- **Throttling (`CRAWL_DELAY`)**: When specified, worker iterations invoke `asyncio.sleep(delay)` to prevent server overloading.
- **Queue Termination**: Workers process URLs until the queue is exhausted (`queue.join()`) and no workers remain active, or until `stop_event` is triggered.

### 2.2 Visited URL Tracking & Deduplication
To prevent infinite loops and duplicate network requests:
- An in-memory set stores normalized string hashes of visited URLs.
- URL normalization rules applied before queue insertion:
  1. Lowercase scheme and domain (`HTTP` -> `http`, `HTTPS` -> `https`).
  2. Strip URL fragments (`#section`).
  3. Standardize trailing slashes according to site configuration.
  4. Preserve meaningful query parameters while stripping transient tracking parameters (`utm_*`, `fbclid`, `gclid`) when configured.
  5. Resolve relative paths against the source document's base URL.

---

## 3. Crawl Modes

The crawler supports three distinct operational modes (`Config.CRAWL_MODE`):

| Mode | Identifier | Description |
| :--- | :--- | :--- |
| **Spider** | `spider` | Default mode. Starts at seed URL, follows discovered hyperlinks recursively within domain scope up to `MAX_PAGES` or `MAX_CRAWL_DEPTH`. |
| **List** | `list` | Crawls an explicit, fixed list of URLs provided via text input or file (`Config.URLS_LIST`). Does not queue newly discovered links. |
| **Sitemap** | `sitemap` | Fetches XML sitemaps discovered in `robots.txt` or supplied directly, parsing all `<loc>` entries and crawling only those URLs. |

---

## 4. Domain & Subdomain Scoping Rules

By default, crawling is restricted to the exact domain and subdomain of the seed URL:
- **Subdomain Crawling (`CRAWL_SUBDOMAINS`)**: When enabled, the crawler traverses internal subdomains (e.g. `blog.example.com`, `shop.example.com` when starting at `example.com`).
- **All Subdomains (`CRAWL_ALL_SUBDOMAINS`)**: Enables traversing across all discovered subdomains of the root domain.
- **Allowed Domains (`ALLOWED_DOMAINS`)**: Explicit list of external domains permitted in scope (useful for multi-domain web properties or localized country domains).
- **Include Regex (`INCLUDE_REGEX`)**: Evaluates regular expressions against candidate URLs; only matching URLs are queued.
- **Exclude Regex (`EXCLUDE_REGEX`)**: Evaluates regular expressions; matching URLs are rejected from the crawl frontier.

---

## 5. Robot Exclusion (`crawler/robots.py`)

Compliance with `robots.txt` is enforced prior to queuing any URL:
1. **Fetching**: Upon initial crawl launch, the engine issues a GET request to `/robots.txt`.
2. **Parsing**: The file is parsed using `urllib.robotparser.RobotFileParser` against the configured User-Agent string.
3. **Evaluation**:
   - Disallowed paths are rejected from the crawl queue.
   - Any `Crawl-delay` directives specified in `robots.txt` automatically set the minimum request interval if higher than `CRAWL_DELAY`.
   - Sitemap references declared via `Sitemap:` directives are extracted and cataloged.
4. **Bypass Option**: When `RESPECT_ROBOTS_TXT = False`, the engine crawls regardless of disallow rules (useful for staging audits).

---

## 6. XML Sitemap Discovery (`crawler/sitemap.py`)

The sitemap subsystem fetches and processes XML sitemaps:
- Handles standard `<urlset>` sitemaps and nested `<sitemapindex>` hierarchies.
- Supports gzipped sitemaps (`.xml.gz`).
- Extracts `<loc>`, `<lastmod>`, `<changefreq>`, and `<priority>` metadata into the `sitemap_entries` database table.
- Feeds discovered sitemap URLs to the analysis pipeline for orphan page detection.

---

## 7. Dynamic JavaScript Rendering (Playwright)

For modern Single Page Applications (React, Vue, Angular, Next.js) where content or navigation is rendered on the client side:
- **Engine**: Headless Chromium managed via `playwright.async_api`.
- **Trigger**: When `JS_RENDER_ENABLED = True`, or when static HTML contains SPA root mounts (`<div id="root"></div>`, `<div id="__next"></div>`, `<app-root></app-root>`) with minimal server-rendered text.
- **Concurrency**: Controlled via a dedicated `asyncio.Semaphore` to prevent Chromium from exhausting system memory.
- **Metrics Captured**:
  - Rendered DOM HTML.
  - Client-side modified title, H1, meta description, canonical, and robots tags.
  - Browser console logs (errors, warnings, debug info).
  - Client-rendered word counts compared against raw HTML word counts.
- **Resource Management**: Browser contexts and tabs are created and closed per URL in `try...finally` blocks to prevent browser context memory leaks.

---

## 8. Bot Emulation & Authentication

### 8.1 User-Agent Presets
The crawler supports several preconfigured User-Agent identities via `config.USER_AGENT_PRESETS`:
- `default`: Chrome Desktop (modern Windows x64).
- `chrome_desktop`: Standard Chrome desktop browser.
- `chrome_mobile`: Mobile Safari / iPhone emulation.
- `googlebot_smartphone`: Googlebot mobile crawler.
- `googlebot_desktop`: Googlebot desktop crawler.
- `bingbot`: Bingbot crawler.
- `custom_crawler`: Custom identification string (`SEOAuditor/2.0`).

### 8.2 HTTP Authentication & Custom Headers
- **Basic Authentication (`HTTP_AUTH`)**: Supports passing HTTP Basic Auth credentials (`username`, `password`) for staging environments or internal intranets.
- **Custom Headers (`CUSTOM_HEADERS`)**: Enables sending custom request headers (e.g. `X-QA-Auth: secret`, cookies, or authorization tokens).
- **Proxy Support (`PROXY`)**: Configurable HTTP and SOCKS5 proxy support for geo-targeted audits or rate-limit evasion.

---

## 9. Redirect Chain Resolution

The crawler tracks full redirect chains to maintain complete link provenance:
- **Max Chain Threshold**: Follows up to 10 redirect hops (`Config.MAX_REDIRECT_CHAIN`).
- **Loop Detection**: Tracks visited URLs in each redirect sequence. If an intermediate URL matches an earlier hop, the chain is flagged as a circular redirect.
- **Relational Storage**: The initial URL, intermediate status codes (301, 302, 307, 308), redirect types (HTTP, HTML meta refresh, JavaScript redirect), and final destination URL are recorded in `pages.redirect_chain_details`.
