# Crawler Engine Specification

## 1. Module Overview

The crawler subsystem resides in `crawler/engine.py` and is responsible for autonomously discovering, fetching, and queuing resources from target web properties. It operates fully asynchronously using Python `asyncio` and `httpx`, enforcing network politeness and robot exclusion rules while maintaining high request concurrency.

Related documentation:
- Data storage: [Database Architecture](database_architecture.md)
- Post-fetch extraction: [Analysis Pipeline](analysis_pipeline.md)
- Telemetry dispatch: [API & WebSocket Protocol](api_and_websocket.md)

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

- **Concurrency Control**: Defaults to `15` concurrent workers, configured via `Config.CRAWL_CONCURRENCY` in `config.py`.
- **Throttling (`CRAWL_DELAY`)**: When specified, worker iterations invoke `asyncio.sleep(delay)` to prevent server overloading.
- **Queue Sentinel**: Workers poll the queue until all discovered links have completed and pending tasks reach zero (`queue.join()`).

### 2.2 Visited URL Tracking & Deduplication
To prevent infinite loops and redundant network calls:
- An in-memory `set` stores canonicalized string hashes of visited URLs.
- URL Normalization rules applied before queue insertion:
  1. Scheme lowercase normalization (`HTTP` -> `http`, `HTTPS` -> `https`).
  2. Domain lowercase conversion.
  3. Strip URL fragments (`#section`).
  4. Consistent trailing slash standardization.
  5. Removal of transient tracking parameters (e.g. `utm_*`, `fbclid`, `gclid`) when configured.

---

## 3. Robot Exclusion (`crawler/robots.py`)

Compliance with `robots.txt` is enforced prior to queuing any URL:
1. **Fetching**: Upon initial crawl launch, the engine issues a GET request to `/robots.txt`.
2. **Parsing**: The file is parsed against the active User-Agent string (e.g. `Config.USER_AGENT`).
3. **Evaluation**:
   - Disallowed paths are rejected immediately.
   - Crawl-delay directives within `robots.txt` automatically override default concurrency if higher.
   - Sitemap references are extracted and registered into the seed queue.

---

## 4. Redirect Chain Resolution

The crawler tracks full redirect chains to maintain complete link provenance:
- **Max Chain Threshold**: Follows up to 10 redirect hops (`Config.MAX_REDIRECT_CHAIN`).
- **Loop Detection**: Maintains a list of intermediate URLs. If an intermediate URL matches an earlier hop, the chain is aborted and logged as a Circular Redirect.
- **Relational Storage**: The initial URL, intermediate 3xx status codes, and final destination URL are preserved in `pages.redirect_url` and `pages.status_code`.

---

## 5. Network Resilience and Error Recovery

- **Connection Timeouts**: Defaults to 10 seconds per request (`Config.REQUEST_TIMEOUT`).
- **Rate-Limit Handling (HTTP 429)**: Automatically triggers exponential backoff, delaying worker operations before retrying the affected URL.
- **Transient Failures**: Network dropouts and SSL handshakes are retried up to 2 times before logging a client failure status code (`0` or `599`).
