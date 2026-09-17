import asyncio
import logging
import time
import hashlib
import json
import re
from typing import Optional, List, Set, Dict, Any, Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin, urldefrag, parse_qs, urlencode

import httpx
from bs4 import BeautifulSoup

from .robots import RobotsParser
from .sitemap import SitemapParser
from config import USER_AGENT_PRESETS

logger = logging.getLogger(__name__)

@dataclass
class PageResponse:
    url: str
    final_url: str
    status_code: int
    headers: Dict[str, str]
    html: str
    response_time_ms: float
    content_type: str
    redirect_chain: List[str]
    raw_html_hash: str = ""
    rendered_html_hash: str = ""
    http_version: str = "HTTP/1.1"
    headers_json: str = "{}"
    cookies_json: str = "{}"
    x_robots_tag: Optional[str] = None
    http_canonical: Optional[str] = None
    size_bytes: int = 0
    transferred_bytes: int = 0
    redirect_type: Optional[str] = None
    redirect_chain_details: List[Dict[str, Any]] = field(default_factory=list)
    tls_protocol: Optional[str] = None
    server_header: Optional[str] = None

@dataclass
class ParsedPage:
    title: Optional[str] = None
    title_length: int = 0
    meta_description: Optional[str] = None
    meta_description_length: int = 0
    meta_keywords: Optional[str] = None
    meta_keywords_length: int = 0
    meta_robots: Optional[str] = None
    canonical: Optional[str] = None
    h1_h6: Dict[str, List[str]] = field(default_factory=dict)
    h1_count: int = 0
    h1_length: int = 0
    h2_count: int = 0
    h2_length: int = 0
    word_count: int = 0
    sentence_count: int = 0
    avg_words_per_sentence: float = 0.0
    text_ratio: float = 0.0
    content_hash: str = ""
    content_near_duplicate_hash: str = ""
    links: List[Dict[str, str]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    structured_data: List[str] = field(default_factory=list)
    meta_tags: List[Dict[str, str]] = field(default_factory=list)
    viewport: Optional[str] = None
    has_media_queries: bool = True
    language: Optional[str] = None
    resources: List[Dict[str, Any]] = field(default_factory=list)
    custom_extractions: List[Dict[str, str]] = field(default_factory=list)
    custom_searches: List[Dict[str, Any]] = field(default_factory=list)
    pagination_tags: List[Dict[str, str]] = field(default_factory=list)
    hreflang_tags: List[Dict[str, str]] = field(default_factory=list)
    mobile_alt_link: Optional[str] = None
    amp_html_link: Optional[str] = None
    rendered_title: Optional[str] = None
    rendered_meta_description: Optional[str] = None
    rendered_h1: Optional[str] = None
    rendered_canonical: Optional[str] = None
    rendered_meta_robots: Optional[str] = None
    rendered_word_count: Optional[int] = None
    console_logs: List[Dict[str, Any]] = field(default_factory=list)
    og_tags: Dict[str, str] = field(default_factory=dict)
    twitter_tags: Dict[str, str] = field(default_factory=dict)
    forms: List[Dict[str, Any]] = field(default_factory=list)
    iframes: List[Dict[str, str]] = field(default_factory=list)
    microdata: List[Dict[str, Any]] = field(default_factory=list)
    rdfa: List[Dict[str, Any]] = field(default_factory=list)
    security_headers: Dict[str, str] = field(default_factory=dict)
    plaintext_emails: List[str] = field(default_factory=list)


class CrawlEngine:
    def __init__(self, start_url: str, config: Any, database: Any, progress_callback: Optional[Callable] = None, audit_id: Optional[str] = None, stop_event: Optional[asyncio.Event] = None):
        self.start_url = start_url
        self.config = config
        self.database = database
        self.progress_callback = progress_callback
        self.audit_id = audit_id
        self.stop_event = stop_event or asyncio.Event()
        
        self.parsed_start = urlparse(start_url)
        self.domain = self.parsed_start.netloc
        self.scheme = self.parsed_start.scheme
        self.base_url = f"{self.scheme}://{self.domain}"
        
        timeout = getattr(self.config, 'REQUEST_TIMEOUT', 30)
        
        # User Agent & Bot Emulation
        ua_preset = getattr(self.config, 'USER_AGENT_PRESET', 'default')
        self.user_agent = USER_AGENT_PRESETS.get(ua_preset, getattr(self.config, 'USER_AGENT', 'SEOAuditor/1.0'))
        
        # MAX_PAGES = 0 means unlimited (no cap)
        self.max_pages = getattr(self.config, 'MAX_PAGES', 0)
        self.crawl_delay = getattr(self.config, 'CRAWL_DELAY', 0.0)
        self.crawl_mode = getattr(self.config, 'CRAWL_MODE', 'spider')
        max_concurrency = getattr(self.config, 'CRAWL_CONCURRENCY', 15)
        
        # HTML size cap: skip parsing pages larger than this (bytes)
        self.max_html_size = getattr(self.config, 'MAX_HTML_SIZE', 5 * 1024 * 1024)  # 5MB
        
        # Staging Auth & Realistic Browser Headers
        client_headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
        custom_headers = getattr(self.config, 'CUSTOM_HEADERS', {})
        if custom_headers:
            client_headers.update(custom_headers)
            
        auth = None
        http_auth = getattr(self.config, 'HTTP_AUTH', None)
        if http_auth and 'username' in http_auth and 'password' in http_auth:
            auth = httpx.BasicAuth(http_auth['username'], http_auth['password'])
            
        proxy = getattr(self.config, 'PROXY', None)
        limits = httpx.Limits(max_keepalive_connections=100, max_connections=200, keepalive_expiry=30.0)
        
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=client_headers,
            auth=auth,
            proxy=proxy,
            limits=limits,
            verify=False
        )
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.frontier: asyncio.Queue[tuple] = asyncio.Queue()  # (url, depth, parent_url)
        self.frontier_refill_lock = asyncio.Lock()
        self.visited: Set[int] = set()
        self.robots_parser = RobotsParser(self.base_url)

        # Persistent Playwright browser instance pool
        self.playwright = None
        self.browser = None
        self.browser_lock = asyncio.Lock()
        js_concurrency = getattr(self.config, 'JS_CONCURRENCY', 3)
        self.playwright_semaphore = asyncio.Semaphore(js_concurrency)

    def _url_hash(self, url: str) -> int:
        """Compute compact 64-bit integer hash for memory-efficient deduplication."""
        return int(hashlib.md5(url.encode('utf-8')).hexdigest()[:16], 16)

    async def _get_browser(self):
        """Lazy-instantiate single persistent Chromium browser instance for all workers."""
        if self.browser is not None:
            return self.browser
        async with self.browser_lock:
            if self.browser is not None:
                return self.browser
            try:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
                )
                return self.browser
            except ImportError:
                logger.warning("Playwright not installed, skipping JS rendering.")
                return None
            except Exception as e:
                logger.error(f"Failed to launch Playwright browser: {e}")
                return None

    async def _refill_frontier(self, audit_id: str, limit: int = 150):
        """Refill in-memory worker queue buffer from persistent SQLite crawl_frontier."""
        async with self.frontier_refill_lock:
            if self.frontier.qsize() >= 50:
                return
            batch = await self.database.pop_frontier_batch(audit_id, limit=limit)
            for row in batch:
                u = row['url']
                if self._url_hash(u) not in self.visited:
                    self.frontier.put_nowait((u, row['depth'], row['parent_url']))

    async def crawl(self, audit_id: Optional[str] = None) -> str:
        """Main crawl loop. Returns audit_id."""
        import uuid
        import json
        from datetime import datetime
        import re
        
        audit_id = audit_id or self.audit_id or str(uuid.uuid4())
        self.audit_id = audit_id
        
        existing = await self.database.get_audit(audit_id)
        if not existing:
            config_json = json.dumps({
                'start_url': self.start_url,
                'max_pages': self.max_pages,
                'concurrency': getattr(self.config, 'CRAWL_CONCURRENCY', 5),
                'crawl_mode': self.crawl_mode,
                'user_agent': self.user_agent,
            })
            await self.database.create_audit(
                audit_id=audit_id,
                domain=self.domain,
                url=self.start_url,
                config=config_json
            )
        await self.database.update_audit(audit_id, status='crawling', started_at=datetime.utcnow().isoformat())
        
        # Populate initial seeds according to CRAWL_MODE
        initial_seeds = []
        now_ts = datetime.utcnow().isoformat()
        if self.crawl_mode == 'list':
            urls_list = getattr(self.config, 'URLS_LIST', [])
            if not urls_list:
                urls_list = [self.start_url]
            for u in urls_list:
                norm_u = self._normalize_url(u.strip(), self.base_url)
                if norm_u:
                    initial_seeds.append((norm_u, 0, None))
        elif self.crawl_mode == 'sitemap':
            start_norm = self._normalize_url(self.start_url, self.base_url)
            initial_seeds.append((start_norm, 0, None))
            await self.robots_parser.fetch_and_parse(self.client)
            sitemaps = self.robots_parser.get_sitemaps()
            if not sitemaps:
                sitemaps = [urljoin(self.base_url, "/sitemap.xml")]
            sitemap_parser = SitemapParser(self.client)
            for sm in sitemaps:
                await sitemap_parser.fetch_and_parse(sm)
            sm_urls = sitemap_parser.get_all_urls()
            sitemap_entries_to_add = []
            for sm_url in sm_urls:
                norm_url = self._normalize_url(sm_url.url, self.base_url)
                sitemap_entries_to_add.append({
                    'audit_id': audit_id,
                    'page_id': None,
                    'page_url': norm_url,
                    'sitemap_url': getattr(sm_url, 'sitemap_url', None) or (sitemaps[0] if sitemaps else None),
                    'lastmod': sm_url.lastmod,
                    'changefreq': sm_url.changefreq,
                    'priority': sm_url.priority
                })
                if norm_url != start_norm and self._should_crawl(norm_url, 0):
                    initial_seeds.append((norm_url, 0, self.start_url))
            if sitemap_entries_to_add:
                await self.database.add_sitemap_entries_batch(sitemap_entries_to_add)
        else:
            # Spider mode: enqueue seed start_norm first so it is crawled first
            start_norm = self._normalize_url(self.start_url, self.base_url)
            initial_seeds.append((start_norm, 0, None))
            await self.robots_parser.fetch_and_parse(self.client)
            sitemaps = self.robots_parser.get_sitemaps()
            if not sitemaps:
                sitemaps = [urljoin(self.base_url, "/sitemap.xml")]
            sitemap_parser = SitemapParser(self.client)
            for sm in sitemaps:
                await sitemap_parser.fetch_and_parse(sm)
            sm_urls = sitemap_parser.get_all_urls()
            sitemap_entries_to_add = []
            for sm_url in sm_urls:
                norm_url = self._normalize_url(sm_url.url, self.base_url)
                sitemap_entries_to_add.append({
                    'audit_id': audit_id,
                    'page_id': None,
                    'page_url': norm_url,
                    'sitemap_url': getattr(sm_url, 'sitemap_url', None) or (sitemaps[0] if sitemaps else None),
                    'lastmod': sm_url.lastmod,
                    'changefreq': sm_url.changefreq,
                    'priority': sm_url.priority
                })
                if norm_url != start_norm and self._should_crawl(norm_url, 1):
                    initial_seeds.append((norm_url, 1, self.start_url))
            if sitemap_entries_to_add:
                await self.database.add_sitemap_entries_batch(sitemap_entries_to_add)

        # Batch insert initial seeds into SQLite frontier
        if initial_seeds:
            seed_batch = [
                {
                    'audit_id': audit_id,
                    'url': u,
                    'depth': d,
                    'parent_url': p,
                    'status': 'pending',
                    'created_at': now_ts
                }
                for u, d, p in initial_seeds
            ]
            await self.database.add_frontier_batch(seed_batch)

        # Refill worker buffer from SQLite frontier
        await self._refill_frontier(audit_id)

        pages_crawled = 0
        active_workers = 0
        crawl_errors = 0
        total_response_ms = 0.0
        
        def _reached_page_limit():
            """Check if we've hit the page cap. max_pages=0 means unlimited."""
            return self.max_pages > 0 and pages_crawled >= self.max_pages
        
        async def worker():
            nonlocal pages_crawled, active_workers, crawl_errors, total_response_ms
            idle_cycles = 0
            while True:
                # Cooperative stop: check if stop was requested
                if self.stop_event.is_set():
                    break
                if _reached_page_limit():
                    break
                try:
                    item = await asyncio.wait_for(self.frontier.get(), timeout=0.5)
                    idle_cycles = 0
                except asyncio.TimeoutError:
                    if self.stop_event.is_set():
                        break
                    idle_cycles += 1
                    # Refill from database frontier if in-memory queue is empty
                    if self.frontier.empty() and not _reached_page_limit():
                        await self._refill_frontier(audit_id)
                        if not self.frontier.empty():
                            idle_cycles = 0
                            continue
                    # Only exit if queue is empty, no pending items in DB, and no active workers
                    if idle_cycles >= 20 and active_workers == 0:
                        pending_in_db = await self.database.get_frontier_count(audit_id, 'pending')
                        if pending_in_db == 0 or _reached_page_limit():
                            break
                        else:
                            await self._refill_frontier(audit_id)
                            idle_cycles = 0
                    continue

                if len(item) == 3:
                    url, depth, parent_url = item
                else:
                    url, depth = item[0], item[1]
                    parent_url = None

                url_hash = self._url_hash(url)
                if url_hash in self.visited:
                    self.frontier.task_done()
                    continue

                self.visited.add(url_hash)
                active_workers += 1

                async with self.semaphore:
                    try:
                        pages_crawled += 1
                        page_resp = await self._fetch_page(url)
                        if page_resp:
                            total_response_ms += page_resp.response_time_ms

                        if page_resp and "text/html" in page_resp.content_type:
                            # Skip excessively large HTML pages (likely not real content)
                            if len(page_resp.html) > self.max_html_size:
                                logger.warning(f"Skipping oversized HTML ({len(page_resp.html)} bytes): {url}")
                                await self.database.mark_frontier_status(audit_id, url, 'skipped')
                                active_workers -= 1
                                self.frontier.task_done()
                                continue

                            raw_hash = hashlib.md5(page_resp.html.encode("utf-8")).hexdigest()
                            page_resp.raw_html_hash = raw_hash
                            rendered_hash = raw_hash

                            parsed = await self._parse_page(page_resp)

                            needs_js = await self._detect_js_rendering_needed(page_resp.html)
                            if needs_js and getattr(self.config, 'JS_RENDER_ENABLED', True):
                                rend_res = await self._fetch_with_playwright(url)
                                if rend_res and isinstance(rend_res, dict):
                                    page_resp.html = rend_res['html']
                                    rendered_hash = hashlib.md5(rend_res['html'].encode("utf-8")).hexdigest()
                                    page_resp.rendered_html_hash = rendered_hash
                                    parsed.rendered_title = rend_res.get('rendered_title')
                                    parsed.rendered_h1 = rend_res.get('rendered_h1')
                                    parsed.rendered_meta_description = rend_res.get('rendered_meta_desc')
                                    parsed.rendered_canonical = rend_res.get('rendered_canonical')
                                    parsed.rendered_meta_robots = rend_res.get('rendered_meta_robots')
                                    parsed.rendered_word_count = rend_res.get('rendered_word_count')
                                    parsed.console_logs = rend_res.get('console_logs', [])

                            is_indexable = True
                            if parsed.meta_robots and 'noindex' in parsed.meta_robots.lower():
                                is_indexable = False
                            if page_resp.x_robots_tag and 'noindex' in page_resp.x_robots_tag.lower():
                                is_indexable = False

                            mime_val = page_resp.content_type.split(';')[0].strip() if page_resp.content_type else 'text/html'
                            parsed_u = urlparse(page_resp.final_url)
                            folder_depth = len([s for s in parsed_u.path.strip('/').split('/') if s])
                            pretty_url = f"{parsed_u.scheme}://{parsed_u.netloc}{parsed_u.path.rstrip('/') if parsed_u.path != '/' else '/'}"
                            ugly_url = page_resp.final_url

                            html_wc = parsed.word_count
                            rend_wc = parsed.rendered_word_count if parsed.rendered_word_count is not None else html_wc
                            wc_change = rend_wc - html_wc
                            js_wc_pct = round((wc_change / max(1, rend_wc)) * 100, 2) if rend_wc > html_wc else 0.0

                            js_err_count = sum(1 for l in parsed.console_logs if l.get('level') == 'error')
                            js_warn_count = sum(1 for l in parsed.console_logs if l.get('level') in ('warning', 'warn'))
                            js_info_count = sum(1 for l in parsed.console_logs if l.get('level') == 'info')
                            js_debug_count = sum(1 for l in parsed.console_logs if l.get('level') in ('debug', 'verbose'))

                            page_id = await self.database.add_page(
                                audit_id,
                                url=page_resp.final_url,
                                status_code=page_resp.status_code,
                                content_type=page_resp.content_type,
                                response_time_ms=page_resp.response_time_ms,
                                html_size=len(page_resp.html),
                                word_count=parsed.word_count,
                                title=parsed.title,
                                title_length=parsed.title_length,
                                meta_description=parsed.meta_description,
                                meta_description_length=parsed.meta_description_length,
                                meta_keywords=parsed.meta_keywords,
                                meta_keywords_length=parsed.meta_keywords_length,
                                h1=parsed.h1_h6.get('h1', [''])[0] if parsed.h1_h6.get('h1') else None,
                                h1_count=parsed.h1_count,
                                h1_length=parsed.h1_length,
                                h2_count=parsed.h2_count,
                                h2_length=parsed.h2_length,
                                sentence_count=parsed.sentence_count,
                                avg_words_per_sentence=parsed.avg_words_per_sentence,
                                text_ratio=parsed.text_ratio,
                                canonical_url=parsed.canonical,
                                viewport=parsed.viewport,
                                is_indexable=is_indexable,
                                crawl_depth=depth,
                                folder_depth=folder_depth,
                                parent_url=parent_url,
                                language=parsed.language,
                                robots_meta=parsed.meta_robots,
                                mime_type=mime_val,
                                redirect_url=page_resp.final_url if page_resp.final_url != url else None,
                                redirect_chain=json.dumps(page_resp.redirect_chain) if page_resp.redirect_chain else None,
                                redirect_type=page_resp.redirect_type,
                                content_hash=parsed.content_hash,
                                content_near_duplicate_hash=parsed.content_near_duplicate_hash,
                                http_version=page_resp.http_version,
                                headers_json=page_resp.headers_json,
                                cookies_json=page_resp.cookies_json,
                                x_robots_tag=page_resp.x_robots_tag,
                                http_canonical=page_resp.http_canonical,
                                mobile_alt_link=parsed.mobile_alt_link,
                                amp_html_link=parsed.amp_html_link,
                                size_bytes=page_resp.size_bytes,
                                transferred_bytes=page_resp.transferred_bytes,
                                crawl_timestamp=datetime.utcnow().isoformat(),
                                pretty_url=pretty_url,
                                ugly_url=ugly_url,
                                html_word_count=html_wc,
                                rendered_word_count=rend_wc,
                                word_count_change=wc_change,
                                js_word_count_pct=js_wc_pct,
                                html_title=parsed.title,
                                rendered_title=parsed.rendered_title,
                                html_h1=parsed.h1_h6.get('h1', [''])[0] if parsed.h1_h6.get('h1') else None,
                                rendered_h1=parsed.rendered_h1,
                                html_meta_description=parsed.meta_description,
                                rendered_meta_description=parsed.rendered_meta_description,
                                html_canonical=parsed.canonical,
                                rendered_canonical=parsed.rendered_canonical,
                                html_meta_robots=parsed.meta_robots,
                                rendered_meta_robots=parsed.rendered_meta_robots,
                                js_errors=js_err_count,
                                js_warnings=js_warn_count,
                                js_info=js_info_count,
                                js_debug=js_debug_count,
                                js_issues=json.dumps(parsed.console_logs) if parsed.console_logs else None,
                                og_title=parsed.og_tags.get("og:title"),
                                og_description=parsed.og_tags.get("og:description"),
                                og_image=parsed.og_tags.get("og:image"),
                                og_type=parsed.og_tags.get("og:type"),
                                twitter_card=parsed.twitter_tags.get("twitter:card"),
                                twitter_title=parsed.twitter_tags.get("twitter:title"),
                                twitter_description=parsed.twitter_tags.get("twitter:description"),
                                twitter_image=parsed.twitter_tags.get("twitter:image"),
                                hsts_header=parsed.security_headers.get("strict-transport-security"),
                                csp_header=parsed.security_headers.get("content-security-policy"),
                                x_content_type_options=parsed.security_headers.get("x-content-type-options"),
                                x_frame_options=parsed.security_headers.get("x-frame-options"),
                                referrer_policy=parsed.security_headers.get("referrer-policy"),
                                permissions_policy=parsed.security_headers.get("permissions-policy"),
                                tls_protocol=page_resp.tls_protocol,
                                server_header=page_resp.server_header,
                                redirect_chain_details=json.dumps(page_resp.redirect_chain_details) if page_resp.redirect_chain_details else None,
                                form_count=len(parsed.forms),
                                iframe_count=len(parsed.iframes),
                                microdata_json=json.dumps(parsed.microdata) if parsed.microdata else None,
                                rdfa_json=json.dumps(parsed.rdfa) if parsed.rdfa else None,
                                plaintext_emails_json=json.dumps(parsed.plaintext_emails) if parsed.plaintext_emails else None,
                                created_at=datetime.utcnow().isoformat()
                            )

                            if parsed.forms:
                                forms_to_add = [
                                    {
                                        'audit_id': audit_id,
                                        'page_id': page_id,
                                        'page_url': page_resp.final_url,
                                        'action_url': f.get('action'),
                                        'method': f.get('method', 'GET'),
                                        'form_id': f.get('id'),
                                        'has_password': f.get('has_password', False),
                                        'is_search': f.get('is_search', False),
                                        'is_insecure': f.get('is_insecure', False),
                                    }
                                    for f in parsed.forms
                                ]
                                await self.database.add_forms_batch(forms_to_add)

                            for ext in parsed.custom_extractions:
                                await self.database.add_custom_extraction(
                                    audit_id, page_id, page_resp.final_url,
                                    ext['rule_name'], ext['extracted_value']
                                )

                            for sm in parsed.custom_searches:
                                await self.database.add_custom_search_match(
                                    audit_id, page_id, page_resp.final_url,
                                    sm['search_name'], sm['matched'], sm.get('snippet', '')
                                )

                            headings_batch = []
                            for tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                for idx, heading_text in enumerate(parsed.h1_h6.get(tag_name, [])):
                                    headings_batch.append((page_id, tag_name, heading_text, idx))
                            if headings_batch:
                                await self.database.add_headings_batch(headings_batch)

                            links_batch = []
                            frontier_links = []
                            for link in parsed.links:
                                href = link.get("href")
                                if not href or isinstance(href, list):
                                    continue
                                abs_href = self._normalize_url(href, page_resp.final_url)
                                is_internal = self._is_internal_url(abs_href)

                                rel_val = link.get("rel", "")
                                if isinstance(rel_val, list):
                                    rel_val = " ".join(rel_val)
                                nofollow = 'nofollow' in str(rel_val).lower()

                                links_batch.append({
                                    'audit_id': audit_id,
                                    'source_page_id': page_id,
                                    'source_url': page_resp.final_url,
                                    'target_url': abs_href,
                                    'anchor_text': link.get("text", ""),
                                    'is_internal': is_internal,
                                    'is_broken': False,
                                    'status_code': None,
                                    'rel_attributes': str(rel_val),
                                    'link_type': link.get("tag", "a"),
                                    'nofollow': nofollow
                                })

                                # Queue internal URLs into persistent frontier if in spider mode
                                if is_internal and self.crawl_mode == 'spider' and self._should_crawl(abs_href, depth + 1):
                                    frontier_links.append({
                                        'audit_id': audit_id,
                                        'url': abs_href,
                                        'depth': depth + 1,
                                        'parent_url': page_resp.final_url,
                                        'status': 'pending',
                                        'created_at': datetime.utcnow().isoformat()
                                    })

                            if links_batch:
                                await self.database.add_links_batch(links_batch)
                            if frontier_links:
                                await self.database.add_frontier_batch(frontier_links)
                                if self.frontier.qsize() < 50 and not _reached_page_limit():
                                    await self._refill_frontier(audit_id)


                            images_batch = []
                            for img in parsed.images:
                                src = img.get("src", "")
                                if src:
                                    src = urljoin(page_resp.final_url, src)
                                images_batch.append({
                                    'audit_id': audit_id,
                                    'page_id': page_id,
                                    'page_url': page_resp.final_url,
                                    'src': src,
                                    'alt_text': img.get("alt"),
                                    'file_size': None,
                                    'width': int(img["width"]) if img.get("width", "").isdigit() else None,
                                    'height': int(img["height"]) if img.get("height", "").isdigit() else None,
                                    'format': src.split('.')[-1].lower() if '.' in src else None,
                                    'is_lazy_loaded': 'loading' in str(img) and 'lazy' in str(img.get('loading', '')),
                                    'has_dimensions': bool(img.get("width") and img.get("height")),
                                    'is_broken': False
                                })
                            if images_batch:
                                await self.database.add_images_batch(images_batch)

                            for sd in parsed.structured_data:
                                try:
                                    sd_parsed = json.loads(sd)
                                    schema_type = sd_parsed.get('@type', 'Unknown') if isinstance(sd_parsed, dict) else 'Unknown'
                                    await self.database.add_structured_data(
                                        audit_id, page_id,
                                        page_url=page_resp.final_url,
                                        format='json-ld',
                                        schema_type=schema_type,
                                        data_json=sd,
                                        is_valid=True,
                                        errors=None
                                    )
                                except json.JSONDecodeError:
                                    await self.database.add_structured_data(
                                        audit_id, page_id,
                                        page_url=page_resp.final_url,
                                        format='json-ld',
                                        schema_type='Invalid',
                                        data_json=sd,
                                        is_valid=False,
                                        errors='Invalid JSON-LD syntax'
                                    )

                            for res in parsed.resources:
                                res_url = res.get("href") or res.get("src")
                                if res_url:
                                    res_type = 'css' if res.get("rel") == ['stylesheet'] else ('js' if res.get("tag") == 'script' else 'other')
                                    await self.database.add_resource(
                                        audit_id, page_id,
                                        url=urljoin(page_resp.final_url, res_url) if res_url else None,
                                        resource_type=res_type,
                                        size=None,
                                        is_render_blocking=res.get("blocking", False),
                                        is_minified=None,
                                        cache_control=None
                                    )

                            # Pagination tags
                            if parsed.pagination_tags:
                                p_batch = [{
                                    'audit_id': audit_id,
                                    'page_id': page_id,
                                    'page_url': page_resp.final_url,
                                    'rel_type': p['rel_type'],
                                    'target_url': p['target_url'],
                                    'source': p.get('source', 'html')
                                } for p in parsed.pagination_tags]
                                await self.database.add_pagination_tags_batch(p_batch)

                            # Hreflang tags
                            for hf in parsed.hreflang_tags:
                                await self.database.add_hreflang(
                                    audit_id=audit_id,
                                    page_id=page_id,
                                    source_url=page_resp.final_url,
                                    target_url=hf['target_url'],
                                    lang_code=hf['lang_code'],
                                    is_self=(hf['target_url'] == page_resp.final_url)
                                )

                            # Console logs
                            if parsed.console_logs:
                                c_logs = [{
                                    'audit_id': audit_id,
                                    'page_id': page_id,
                                    'page_url': page_resp.final_url,
                                    'level': l.get('level', 'info'),
                                    'message': l.get('message', ''),
                                    'source': l.get('source', 'javascript'),
                                    'line_number': l.get('line_number'),
                                    'timestamp': datetime.utcnow().isoformat()
                                } for l in parsed.console_logs]
                                await self.database.add_console_logs_batch(c_logs)

                        elif page_resp:
                            parsed_u = urlparse(page_resp.final_url)
                            folder_depth = len([s for s in parsed_u.path.strip('/').split('/') if s])
                            pretty_url = f"{parsed_u.scheme}://{parsed_u.netloc}{parsed_u.path.rstrip('/') if parsed_u.path != '/' else '/'}"
                            ugly_url = page_resp.final_url

                            await self.database.add_page(
                                audit_id,
                                url=page_resp.final_url,
                                status_code=page_resp.status_code,
                                content_type=page_resp.content_type,
                                response_time_ms=page_resp.response_time_ms,
                                html_size=0,
                                word_count=0,
                                crawl_depth=depth,
                                folder_depth=folder_depth,
                                parent_url=parent_url,
                                http_version=page_resp.http_version,
                                headers_json=page_resp.headers_json,
                                cookies_json=page_resp.cookies_json,
                                x_robots_tag=page_resp.x_robots_tag,
                                http_canonical=page_resp.http_canonical,
                                size_bytes=page_resp.size_bytes,
                                transferred_bytes=page_resp.transferred_bytes,
                                redirect_url=page_resp.final_url if page_resp.final_url != url else None,
                                redirect_chain=json.dumps(page_resp.redirect_chain) if page_resp.redirect_chain else None,
                                redirect_type=page_resp.redirect_type,
                                redirect_chain_details=json.dumps(page_resp.redirect_chain_details) if page_resp.redirect_chain_details else None,
                                tls_protocol=page_resp.tls_protocol,
                                server_header=page_resp.server_header,
                                pretty_url=pretty_url,
                                ugly_url=ugly_url,
                                crawl_timestamp=datetime.utcnow().isoformat(),
                                created_at=datetime.utcnow().isoformat()
                            )

                        await self.database.mark_frontier_status(audit_id, url, 'done')

                        # Immediate flush for live data population
                        await self.database.flush()

                        # WAL checkpoint every 500 pages to prevent unbounded WAL growth
                        if pages_crawled % 500 == 0:
                            try:
                                await self.database.wal_checkpoint()
                            except Exception:
                                pass

                        if self.progress_callback:
                            pending_count = await self.database.get_frontier_count(audit_id, 'pending')
                            raw_total = max(pages_crawled, len(self.visited) + pending_count + self.frontier.qsize())
                            active_total = min(self.max_pages, raw_total) if self.max_pages > 0 else raw_total
                            avg_response = round(total_response_ms / max(1, pages_crawled), 1)
                            import psutil, os
                            try:
                                mem_mb = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 1)
                            except Exception:
                                mem_mb = 0
                            progress_data = {
                                "crawled": pages_crawled,
                                "total": active_total,
                                "url": url,
                                "queued": pending_count + self.frontier.qsize(),
                                "errors": crawl_errors,
                                "avg_response_ms": avg_response,
                                "memory_mb": mem_mb,
                                "visited_count": len(self.visited),
                            }
                            if asyncio.iscoroutinefunction(self.progress_callback):
                                await self.progress_callback(progress_data)
                            else:
                                self.progress_callback(progress_data)

                        if self.crawl_delay > 0:
                            await asyncio.sleep(self.crawl_delay)

                    except Exception as e:
                        crawl_errors += 1
                        logger.error(f"Error processing {url}: {e}", exc_info=True)
                        await self.database.mark_frontier_status(audit_id, url, 'failed')
                    finally:
                        active_workers -= 1
                        self.frontier.task_done()

        num_workers = getattr(self.config, 'CRAWL_CONCURRENCY', 15)
        workers = [asyncio.create_task(worker()) for _ in range(num_workers)]

        try:
            # Wait for all workers to finish naturally
            await asyncio.gather(*workers, return_exceptions=True)
        finally:
            if self.browser:
                try:
                    await self.browser.close()
                except Exception:
                    pass
                self.browser = None
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception:
                    pass
                self.playwright = None

        # Resolve actual file sizes for images and CSS/JS resources via HEAD requests
        try:
            await self._resolve_resource_sizes(audit_id)
        except Exception as e:
            logger.warning(f"Resource size resolution skipped: {e}")

        await self.client.aclose()

        # Final flush of any pending writes
        await self.database.flush()

        # Determine final status based on whether stop was requested
        was_stopped = self.stop_event.is_set()
        final_status_label = "Stopped by user. Analyzing crawled pages..." if was_stopped else "Crawl complete. Analyzing pages..."

        # Notify progress callback that crawl completed and analysis begins
        if self.progress_callback:
            try:
                cb_payload = {"crawled": pages_crawled, "total": pages_crawled, "url": final_status_label, "status": "analyzing"}
                if asyncio.iscoroutinefunction(self.progress_callback):
                    await self.progress_callback(cb_payload)
                else:
                    self.progress_callback(cb_payload)
            except Exception:
                pass

        await self.database.update_audit(
            audit_id,
            status='analyzing',
            completed_at=datetime.utcnow().isoformat(),
            total_pages=pages_crawled
        )

        return audit_id

    async def _resolve_resource_sizes(self, audit_id: str):
        """Batch HEAD requests to images and resources to resolve actual file sizes and status."""
        logger.info(f"Resolving image and resource file sizes for audit {audit_id}...")
        try:
            images = await self.database.get_images(audit_id)
            resources = await self.database.get_resources(audit_id)

            urls_to_check: Dict[str, List[tuple]] = {}
            for img in images:
                src = img.get('src')
                if src and img.get('file_size') is None and src.startswith(('http://', 'https://')):
                    urls_to_check.setdefault(src, []).append(('image', img['id']))

            for res in resources:
                r_url = res.get('url')
                if r_url and res.get('size') is None and r_url.startswith(('http://', 'https://')):
                    urls_to_check.setdefault(r_url, []).append(('resource', res['id']))

            targets = list(urls_to_check.items())[:250]
            if not targets:
                return

            sem = asyncio.Semaphore(20)
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, limits=httpx.Limits(max_connections=25)) as res_client:
                async def _probe(url_item):
                    u, targets_list = url_item
                    async with sem:
                        size = None
                        status = 0
                        try:
                            resp = await res_client.head(u)
                            status = resp.status_code
                            cl = resp.headers.get("content-length")
                            if cl and cl.isdigit():
                                size = int(cl)
                            elif resp.status_code == 200:
                                g_resp = await res_client.get(u)
                                size = len(g_resp.content)
                                status = g_resp.status_code
                        except Exception:
                            status = 0
                        return u, targets_list, size, status

                results = await asyncio.gather(*[_probe(item) for item in targets], return_exceptions=True)
                for res in results:
                    if isinstance(res, tuple):
                        u, targets_list, size, status = res
                        for item_type, item_id in targets_list:
                            if item_type == 'image':
                                is_broken = (status >= 400 or status == 0) if status else False
                                await self.database.update_image_size(item_id, size or 0, is_broken=is_broken)
                            elif item_type == 'resource':
                                if size is not None:
                                    await self.database.update_resource_size(item_id, size)

        except Exception as e:
            logger.warning(f"Error resolving resource sizes: {e}")

    async def _fetch_page(self, url: str) -> Optional[PageResponse]:
        if not self.robots_parser.is_allowed(url, self.user_agent):
            logger.info(f"Blocked by robots.txt: {url}")
            return None
            
        start_time = time.time()
        max_retries = 3
        resp = None

        for attempt in range(max_retries + 1):
            try:
                resp = await self.client.get(url)
                if resp.status_code in (429, 503) and attempt < max_retries:
                    retry_after = resp.headers.get("retry-after")
                    backoff = None
                    if retry_after:
                        try:
                            backoff = min(float(retry_after), 60.0)
                        except ValueError:
                            pass
                    if backoff is None:
                        backoff = min(2.0 ** (attempt + 1), 30.0)
                    logger.warning(f"Received HTTP {resp.status_code} for {url}. Backing off for {backoff:.1f}s (retry {attempt+1}/{max_retries})")
                    await asyncio.sleep(backoff)
                    continue
                break
            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt < max_retries:
                    wait_sec = 1.0 * (attempt + 1)
                    logger.warning(f"Connection issue on {url} ({e}). Retrying in {wait_sec:.1f}s (retry {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_sec)
                    continue
                logger.error(f"Request error fetching {url}: {e}")
                return None

        if resp is None:
            return None

        elapsed_ms = (time.time() - start_time) * 1000
        
        chain = [str(r.url) for r in resp.history] if resp.history else []
        headers_dict = dict(resp.headers)
        headers_json = json.dumps(headers_dict)
        try:
            cookies_dict = {c.name: c.value for c in getattr(resp.cookies, 'jar', resp.cookies)}
        except Exception:
            cookies_dict = {}
        cookies_json = json.dumps(cookies_dict)
        http_version = getattr(resp, 'http_version', 'HTTP/1.1')
        x_robots_tag = resp.headers.get("x-robots-tag")

        # HTTP Canonical link header: Link: <https://example.com/page>; rel="canonical"
        http_canonical = None
        link_header = resp.headers.get("link", "")
        if link_header:
            m = re.search(r'<([^>]+)>;\s*rel=["\']?canonical["\']?', link_header, re.IGNORECASE)
            if m:
                http_canonical = m.group(1).strip()

        size_bytes = len(resp.content) if hasattr(resp, 'content') and resp.content else len(resp.text.encode('utf-8'))
        transferred_bytes = size_bytes
        if "content-length" in resp.headers:
            try:
                transferred_bytes = int(resp.headers["content-length"])
            except Exception:
                pass

        redirect_type = None
        chain_details = []
        if resp.history:
            for r in resp.history:
                r_code = r.status_code
                r_label = "Permanent" if r_code in (301, 308) else "Temporary"
                chain_details.append({
                    "url": str(r.url),
                    "status": r_code,
                    "type": f"{r_code} {r_label}"
                })
            last_hist = resp.history[-1]
            code = last_hist.status_code
            if code == 301:
                redirect_type = "301 Permanent"
            elif code == 302:
                redirect_type = "302 Found"
            elif code == 307:
                redirect_type = "307 Temporary"
            elif code == 308:
                redirect_type = "308 Permanent"
            else:
                redirect_type = f"{code} Redirect"

        if chain_details:
            chain_details.append({
                "url": str(resp.url),
                "status": resp.status_code,
                "type": "Final"
            })

        server_header = resp.headers.get("server")
        tls_proto = None
        try:
            raw_stream = getattr(resp, "_raw_stream", None)
            stream = getattr(raw_stream, "stream", None) or getattr(raw_stream, "_stream", None)
            sock = getattr(stream, "socket", None) or getattr(stream, "_sock", None)
            if sock and hasattr(sock, "version"):
                tls_proto = sock.version()
        except Exception:
            tls_proto = None

        return PageResponse(
            url=url,
            final_url=str(resp.url),
            status_code=resp.status_code,
            headers=headers_dict,
            html=resp.text,
            response_time_ms=elapsed_ms,
            content_type=resp.headers.get("content-type", ""),
            redirect_chain=chain,
            http_version=str(http_version),
            headers_json=headers_json,
            cookies_json=cookies_json,
            x_robots_tag=x_robots_tag,
            http_canonical=http_canonical,
            size_bytes=size_bytes,
            transferred_bytes=transferred_bytes,
            redirect_type=redirect_type,
            redirect_chain_details=chain_details,
            tls_protocol=tls_proto,
            server_header=server_header
        )


    async def _parse_page(self, page_response: PageResponse) -> ParsedPage:
        soup = BeautifulSoup(page_response.html, "lxml")
        parsed = ParsedPage()
        
        title_tag = soup.find("title")
        parsed.title = title_tag.text.strip() if title_tag else None
        parsed.title_length = len(parsed.title) if parsed.title else 0
        
        desc_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
        parsed.meta_description = desc_tag.get("content", "").strip() if desc_tag and desc_tag.get("content") else None
        parsed.meta_description_length = len(parsed.meta_description) if parsed.meta_description else 0

        kw_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "keywords"})
        parsed.meta_keywords = kw_tag.get("content", "").strip() if kw_tag and kw_tag.get("content") else None
        parsed.meta_keywords_length = len(parsed.meta_keywords) if parsed.meta_keywords else 0
        
        robots_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "robots"})
        parsed.meta_robots = robots_tag.get("content", "").strip() if robots_tag and robots_tag.get("content") else None
        
        canonical_tag = soup.find("link", attrs={"rel": lambda v: v and "canonical" in (v if isinstance(v, list) else [v])})
        parsed.canonical = canonical_tag.get("href", "").strip() if canonical_tag and canonical_tag.get("href") else None
        
        vp_tag = soup.find("meta", attrs={"name": "viewport"})
        parsed.viewport = vp_tag.get("content", "").strip() if vp_tag and vp_tag.get("content") else None
        
        html_tag = soup.find("html")
        parsed.language = html_tag.get("lang", "").strip() if html_tag and html_tag.has_attr("lang") else None
        if not parsed.language:
            meta_lang = soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "content-language"})
            if meta_lang and meta_lang.has_attr("content"):
                parsed.language = meta_lang.get("content", "").strip()
        
        has_mq = False
        for s in soup.find_all("style"):
            if s.string and "@media" in s.string:
                has_mq = True
                break
        if not has_mq and soup.find_all("link", attrs={"media": True}):
            has_mq = True
        if not has_mq and "@media" in (page_response.html or ""):
            has_mq = True
        parsed.has_media_queries = has_mq
        
        for i in range(1, 7):
            tags = soup.find_all(f"h{i}")
            parsed.h1_h6[f"h{i}"] = [t.get_text(strip=True) for t in tags if t.get_text(strip=True)]
            
        parsed.h1_count = len(parsed.h1_h6.get("h1", []))
        parsed.h1_length = len(parsed.h1_h6["h1"][0]) if parsed.h1_count > 0 else 0
        parsed.h2_count = len(parsed.h1_h6.get("h2", []))
        parsed.h2_length = len(parsed.h1_h6["h2"][0]) if parsed.h2_count > 0 else 0

        text_content = soup.get_text(separator=" ")
        words = [w for w in text_content.split() if w.strip()]
        parsed.word_count = len(words)
        parsed.content_hash = hashlib.md5(" ".join(words).encode("utf-8")).hexdigest()
        parsed.content_near_duplicate_hash = f"{self._compute_simhash(text_content):016x}"
        
        sentences = [s.strip() for s in re.split(r'[\.\!\?]+', text_content) if len(s.strip()) > 3]
        parsed.sentence_count = len(sentences)
        parsed.avg_words_per_sentence = round(parsed.word_count / max(1, parsed.sentence_count), 2)
        raw_len = len(page_response.html or "")
        parsed.text_ratio = round((len(text_content.strip()) / max(1, raw_len)) * 100, 2)

        # Mobile alternate link
        mob_alt = soup.find("link", attrs={"rel": lambda v: v and "alternate" in (v if isinstance(v, list) else [v]), "media": True})
        if mob_alt and mob_alt.get("href"):
            parsed.mobile_alt_link = self._normalize_url(mob_alt.get("href").strip(), page_response.final_url)

        # AMP HTML link
        amp_tag = soup.find("link", attrs={"rel": lambda v: v and "amphtml" in str(v).lower()})
        if amp_tag and amp_tag.get("href"):
            parsed.amp_html_link = self._normalize_url(amp_tag.get("href").strip(), page_response.final_url)

        # Pagination tags (rel="next" / rel="prev") from HTML and HTTP Link header
        for rel_val in ["next", "prev"]:
            tag = soup.find("link", attrs={"rel": lambda v: v and rel_val in (v if isinstance(v, list) else [v])})
            if tag and tag.get("href"):
                parsed.pagination_tags.append({
                    "rel_type": rel_val,
                    "target_url": self._normalize_url(tag.get("href").strip(), page_response.final_url),
                    "source": "html"
                })
        link_h = page_response.headers.get("link", "")
        if link_h:
            for rel_val in ["next", "prev"]:
                m = re.search(r'<([^>]+)>;\s*rel=["\']?' + rel_val + r'["\']?', link_h, re.IGNORECASE)
                if m:
                    parsed.pagination_tags.append({
                        "rel_type": rel_val,
                        "target_url": self._normalize_url(m.group(1).strip(), page_response.final_url),
                        "source": "http_header"
                    })

        # Hreflang tags
        for link_alt in soup.find_all("link", attrs={"rel": lambda v: v and "alternate" in (v if isinstance(v, list) else [v])}):
            lang = link_alt.get("hreflang")
            href = link_alt.get("href")
            if lang and href:
                parsed.hreflang_tags.append({
                    "lang_code": lang.strip(),
                    "target_url": self._normalize_url(href.strip(), page_response.final_url)
                })

        for a in soup.find_all(["a", "area"], href=True):
            href = a.get("href")
            if not href:
                continue
            parsed.links.append({
                "tag": a.name,
                "href": href.strip(),
                "rel": a.get("rel"),
                "hreflang": a.get("hreflang"),
                "text": a.get_text(separator=" ", strip=True)
            })
            
        for img in soup.find_all("img"):
            img_data = {}
            for attr in ["src", "alt", "width", "height"]:
                if img.has_attr(attr):
                    img_data[attr] = img.get(attr)
            parsed.images.append(img_data)
            
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if script.string:
                parsed.structured_data.append(script.string.strip())
                
        for meta in soup.find_all("meta"):
            parsed.meta_tags.append(meta.attrs)
            
        for resource in soup.find_all(["script", "link"]):
            res_data = {"tag": resource.name}
            res_data.update(resource.attrs)
            if resource.name == "script" and resource.has_attr("src"):
                res_data["blocking"] = not (resource.has_attr("async") or resource.has_attr("defer"))
            elif resource.name == "link" and resource.get("rel") == ["stylesheet"]:
                res_data["blocking"] = True
            parsed.resources.append(res_data)
            
        # Custom Extractions (CSS, XPath, Regex)
        custom_rules = getattr(self.config, 'CUSTOM_EXTRACTIONS', [])
        if custom_rules:
            lxml_tree = None
            for rule in custom_rules:
                r_name = rule.get('name', 'unnamed')
                r_type = rule.get('type', 'css').lower()
                r_selector = rule.get('selector', '')
                try:
                    if r_type == 'css':
                        elements = soup.select(r_selector)
                        val = ', '.join([e.get_text(strip=True) for e in elements if e.get_text(strip=True)])
                        if val:
                            parsed.custom_extractions.append({'rule_name': r_name, 'extracted_value': val})
                    elif r_type == 'xpath':
                        if lxml_tree is None:
                            from lxml import html as lxml_html
                            lxml_tree = lxml_html.fromstring(page_response.html)
                        results = lxml_tree.xpath(r_selector)
                        val = ', '.join([str(x).strip() for x in results if str(x).strip()])
                        if val:
                            parsed.custom_extractions.append({'rule_name': r_name, 'extracted_value': val})
                    elif r_type == 'regex':
                        matches = re.findall(r_selector, page_response.html)
                        if matches:
                            val = ', '.join([str(m) for m in matches[:5]])
                            parsed.custom_extractions.append({'rule_name': r_name, 'extracted_value': val})
                except Exception as e:
                    logger.debug(f"Custom extraction error for {r_name}: {e}")

        # Custom Search Rules (Contains / Does Not Contain)
        search_rules = getattr(self.config, 'CUSTOM_SEARCHES', [])
        if search_rules:
            for s_rule in search_rules:
                s_name = s_rule.get('name', 'unnamed')
                s_type = s_rule.get('type', 'contains').lower()
                s_query = s_rule.get('query', '')
                if not s_query:
                    continue
                matched = False
                snippet = ""
                if s_type == 'contains':
                    matched = s_query in page_response.html
                    if matched:
                        idx = page_response.html.find(s_query)
                        snippet = page_response.html[max(0, idx-40):min(len(page_response.html), idx+len(s_query)+40)]
                elif s_type == 'does_not_contain':
                    matched = s_query not in page_response.html
                    if matched:
                        snippet = f"Query '{s_query}' not found in page source"
                parsed.custom_searches.append({
                    'search_name': s_name,
                    'matched': matched,
                    'snippet': snippet
                })

        # Open Graph Tags
        for meta in soup.find_all("meta", attrs={"property": True}):
            prop = str(meta.get("property", "")).lower().strip()
            if prop.startswith("og:"):
                parsed.og_tags[prop] = str(meta.get("content", "")).strip()

        # Twitter Card Tags
        for meta in soup.find_all("meta", attrs={"name": True}):
            name = str(meta.get("name", "")).lower().strip()
            if name.startswith("twitter:"):
                parsed.twitter_tags[name] = str(meta.get("content", "")).strip()

        # Form Discovery
        for form in soup.find_all("form"):
            act = form.get("action", "")
            method = (form.get("method", "GET") or "GET").upper().strip()
            action_url = urljoin(page_response.final_url, act.strip()) if act else page_response.final_url
            has_pwd = bool(form.find("input", attrs={"type": lambda t: t and t.lower() == "password"}))
            is_srch = bool(
                form.find("input", attrs={"type": lambda t: t and t.lower() == "search"})
                or "search" in (form.get("role", "") or "").lower()
                or "search" in (form.get("id", "") or "").lower()
                or "search" in (form.get("name", "") or "").lower()
            )
            is_insecure = (
                page_response.final_url.lower().startswith("https://")
                and action_url.lower().startswith("http://")
            )
            parsed.forms.append({
                "action": action_url,
                "method": method,
                "id": form.get("id", ""),
                "has_password": has_pwd,
                "is_search": is_srch,
                "is_insecure": is_insecure
            })

        # Iframe Discovery
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src", "")
            if src:
                parsed.iframes.append({
                    "src": urljoin(page_response.final_url, src.strip()),
                    "title": iframe.get("title", ""),
                    "loading": iframe.get("loading", "")
                })

        # Microdata (itemscope / itemtype / itemprop)
        for item in soup.find_all(attrs={"itemscope": True}):
            itemtype = item.get("itemtype", "")
            props = {}
            for p in item.find_all(attrs={"itemprop": True}):
                p_name = p.get("itemprop", "")
                if p_name:
                    p_val = p.get("content") or p.get("src") or p.get("href") or p.get_text(strip=True)
                    props[p_name] = str(p_val)[:200]
            parsed.microdata.append({
                "type": itemtype,
                "properties": props
            })

        # RDFa (typeof / property)
        for rdf in soup.find_all(attrs={"typeof": True}):
            rdf_type = rdf.get("typeof", "")
            rdf_props = {}
            for p in rdf.find_all(attrs={"property": True}):
                prop_name = p.get("property", "")
                if prop_name and not prop_name.lower().startswith("og:"):
                    p_val = p.get("content") or p.get("href") or p.get_text(strip=True)
                    rdf_props[prop_name] = str(p_val)[:200]
            if rdf_props:
                parsed.rdfa.append({
                    "type": rdf_type,
                    "properties": rdf_props
                })

        # Security Headers (extracted from page_response.headers)
        security_header_names = [
            'strict-transport-security', 'content-security-policy',
            'x-content-type-options', 'x-frame-options',
            'referrer-policy', 'permissions-policy', 'x-xss-protection'
        ]
        for h_name in security_header_names:
            h_val = page_response.headers.get(h_name)
            if h_val:
                parsed.security_headers[h_name] = h_val

        # Plaintext Email Discovery
        try:
            from services.security_inspector import check_plaintext_emails_sync
            email_res = check_plaintext_emails_sync(page_response.html)
            parsed.plaintext_emails = list(email_res.get('emails', []))
        except Exception:
            pass

        return parsed

    def _normalize_url(self, url: str, base_url: str) -> str:
        absolute = urljoin(base_url, url)
        absolute, _ = urldefrag(absolute)
        
        parsed = urlparse(absolute)
        
        # remove common tracking parameters
        query_params = parse_qs(parsed.query)
        tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid'}
        clean_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        
        clean_query = urlencode(clean_params, doseq=True)
        
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
            
        norm = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
        if clean_query:
            norm += f"?{clean_query}"
            
        return norm

    def _is_internal_url(self, url: str) -> bool:
        parsed = urlparse(url)
        d1 = self.domain.lower()
        d2 = parsed.netloc.lower()
        if d1.startswith('www.'): d1 = d1[4:]
        if d2.startswith('www.'): d2 = d2[4:]

        # Exact domain match
        if d1 == d2:
            return True

        # Subdomain crawling
        if getattr(self.config, 'CRAWL_SUBDOMAINS', False) or getattr(self.config, 'CRAWL_ALL_SUBDOMAINS', False):
            if d2.endswith('.' + d1) or d1.endswith('.' + d2):
                return True

        # Explicit allowed cross-domains
        allowed_domains = getattr(self.config, 'ALLOWED_DOMAINS', [])
        for allowed in allowed_domains:
            a = allowed.lower()
            if a.startswith('www.'): a = a[4:]
            if d2 == a or d2.endswith('.' + a):
                return True

        return False

    def _should_crawl(self, url: str, depth: int = 0) -> bool:
        if not self._is_internal_url(url):
            return False
        if self._url_hash(url) in self.visited:
            return False

        # Block URL list
        block_urls = getattr(self.config, 'BLOCK_URLS', [])
        if block_urls and any(url == bu or url.rstrip('/') == bu.rstrip('/') for bu in block_urls):
            return False

        # Allow URL list (bypass filters)
        allow_urls = getattr(self.config, 'ALLOW_URLS', [])
        if allow_urls and any(url == au or url.rstrip('/') == au.rstrip('/') for au in allow_urls):
            return True

        # Max crawl depth check
        max_depth = getattr(self.config, 'MAX_CRAWL_DEPTH', None)
        if max_depth is not None and depth > max_depth:
            return False
            
        import re
        # Scope: Include regex check (if specified, URL must match at least one)
        include_patterns = getattr(self.config, 'INCLUDE_REGEX', [])
        if include_patterns:
            if not any(re.search(pat, url) for pat in include_patterns if pat.strip()):
                return False
                
        # Scope: Exclude regex check (if specified, URL must not match any)
        exclude_patterns = getattr(self.config, 'EXCLUDE_REGEX', [])
        if exclude_patterns:
            if any(re.search(pat, url) for pat in exclude_patterns if pat.strip()):
                return False
            
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        query_lower = parsed.query.lower()

        # 1. Ignore server & CMS admin paths (e.g. wp-admin, cpanel, etc.)
        server_admin_prefixes = (
            '/wp-admin', '/wp-login', '/wp-includes', '/wp-content/plugins',
            '/xmlrpc.php', '/wp-cron.php', '/readme.html', '/license.txt',
            '/admin', '/administrator', '/cpanel', '/whm', '/phpmyadmin',
            '/webmail', '/server-status', '/server-info', '/cgi-bin',
            '/.git', '/.env', '/.htaccess', '/.user.ini', '/web.config',
        )
        if any(path_lower.startswith(p) or f"{p}/" in path_lower or path_lower.endswith(p) for p in server_admin_prefixes):
            return False

        # 2. Ignore CDN & Cloudflare service endpoints
        cdn_patterns = (
            '/cdn-cgi/', '/cdn/', '/cdn-assets/', '/wp-content/uploads/cache/'
        )
        if any(p in path_lower for p in cdn_patterns):
            return False

        # 3. Ignore action / auth / cart / logout query parameter traps
        action_traps = (
            'action=login', 'action=logout', 'action=register',
            'add-to-cart=', 'wc-ajax=', 'wp_service_worker='
        )
        if any(trap in query_lower for trap in action_traps):
            return False

        # 4. Check CDN subdomains (e.g. cdn.example.com, assets.example.com)
        cdn_subdomains = ('cdn.', 'assets.', 'static.', 'media.', 'images.', 'img.')
        if any(parsed.netloc.lower().startswith(sub) for sub in cdn_subdomains):
            return False

        # 5. Media, document, style, script, and font extensions to ignore
        ext = path_lower.split('.')[-1] if '.' in path_lower else ''
        ignored_extensions = {
            'pdf', 'zip', 'gz', 'tar', 'bz2', '7z', 'rar', 'exe', 'dmg', 'iso', 'bin',
            'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'txt', 'md', 'markdown',
            'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'avif', 'ico', 'bmp', 'tif', 'tiff',
            'mp4', 'mp3', 'wav', 'webm', 'ogg', 'avi', 'mov', 'wmv', 'm4v',
            'css', 'js', 'json', 'xml', 'map', 'woff', 'woff2', 'ttf', 'eot', 'otf',
            'yaml', 'yml', 'rss', 'atom'
        }
        if ext in ignored_extensions:
            return False
            
        if parsed.scheme.lower() in {'mailto', 'tel', 'javascript'}:
            return False
            
        # Trap detection: repeating path segments
        segments = [s for s in parsed.path.split('/') if s]
        if len(segments) > 10 or len(set(segments)) < len(segments) - 3:
            return False
            
        # Trap detection: too many query parameters
        if len(parse_qs(parsed.query)) > 5:
            return False
            
        return True

    async def _detect_js_rendering_needed(self, html: str) -> bool:
        soup = BeautifulSoup(html, "lxml")
        
        text_content = soup.get_text(strip=True)
        if len(text_content) < 500:
            scripts = soup.find_all("script", src=True)
            if len(scripts) > 3:
                return True
                
        if soup.find(id=["root", "app", "__next", "vue-app"]):
            return True
            
        noscript = soup.find("noscript")
        if noscript and "javascript" in noscript.text.lower():
            return True
            
        return False

    async def _fetch_with_playwright(self, url: str) -> Optional[Dict[str, Any]]:
        browser = await self._get_browser()
        if not browser:
            return None

        async with self.playwright_semaphore:
            context = None
            page = None
            try:
                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1280, 'height': 800}
                )
                page = await context.new_page()
                console_logs = []

                def handle_console(msg):
                    try:
                        loc = msg.location
                        console_logs.append({
                            'level': msg.type,
                            'message': msg.text,
                            'source': 'javascript',
                            'line_number': loc.get('lineNumber') if isinstance(loc, dict) else getattr(loc, 'line_number', None)
                        })
                    except Exception:
                        console_logs.append({
                            'level': getattr(msg, 'type', 'info'),
                            'message': getattr(msg, 'text', str(msg)),
                            'source': 'javascript',
                            'line_number': None
                        })

                page.on("console", handle_console)

                await page.goto(url, wait_until="networkidle", timeout=15000)
                content = await page.content()

                rendered_title = await page.title()
                rendered_h1 = await page.evaluate("() => { const h1 = document.querySelector('h1'); return h1 ? h1.innerText.trim() : null; }")
                rendered_meta_desc = await page.evaluate("() => { const m = document.querySelector('meta[name=\"description\"]'); return m ? m.getAttribute('content') : null; }")
                rendered_canonical = await page.evaluate("() => { const c = document.querySelector('link[rel=\"canonical\"]'); return c ? c.getAttribute('href') : null; }")
                rendered_meta_robots = await page.evaluate("() => { const r = document.querySelector('meta[name=\"robots\"]'); return r ? r.getAttribute('content') : null; }")
                rendered_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                rendered_wc = len([w for w in (rendered_text or '').split() if w.strip()])

                return {
                    'html': content,
                    'console_logs': console_logs,
                    'rendered_title': rendered_title,
                    'rendered_h1': rendered_h1,
                    'rendered_meta_desc': rendered_meta_desc,
                    'rendered_canonical': rendered_canonical,
                    'rendered_meta_robots': rendered_meta_robots,
                    'rendered_word_count': rendered_wc
                }
            except Exception as e:
                logger.error(f"Playwright error for {url}: {e}")
                return None
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass


    def _compute_simhash(self, text: str) -> int:
        if not text:
            return 0
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        if not words:
            return 0
        v = [0] * 64
        for word in words:
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest()[:16], 16)
            for i in range(64):
                bit = (h >> i) & 1
                if bit:
                    v[i] += 1
                else:
                    v[i] -= 1
        fingerprint = 0
        for i in range(64):
            if v[i] > 0:
                fingerprint |= (1 << i)
        return fingerprint
