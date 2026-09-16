import asyncio
import logging
import time
import hashlib
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

@dataclass
class ParsedPage:
    title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_robots: Optional[str] = None
    canonical: Optional[str] = None
    h1_h6: Dict[str, List[str]] = field(default_factory=dict)
    word_count: int = 0
    content_hash: str = ""
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


class CrawlEngine:
    def __init__(self, start_url: str, config: Any, database: Any, progress_callback: Optional[Callable] = None, audit_id: Optional[str] = None):
        self.start_url = start_url
        self.config = config
        self.database = database
        self.progress_callback = progress_callback
        self.audit_id = audit_id
        
        self.parsed_start = urlparse(start_url)
        self.domain = self.parsed_start.netloc
        self.scheme = self.parsed_start.scheme
        self.base_url = f"{self.scheme}://{self.domain}"
        
        timeout = getattr(self.config, 'REQUEST_TIMEOUT', 30)
        
        # User Agent & Bot Emulation
        ua_preset = getattr(self.config, 'USER_AGENT_PRESET', 'default')
        self.user_agent = USER_AGENT_PRESETS.get(ua_preset, getattr(self.config, 'USER_AGENT', 'SEOAuditor/1.0'))
        
        self.max_pages = getattr(self.config, 'MAX_PAGES', 5000)
        self.crawl_delay = getattr(self.config, 'CRAWL_DELAY', 0.0)
        self.crawl_mode = getattr(self.config, 'CRAWL_MODE', 'spider')
        max_concurrency = getattr(self.config, 'CRAWL_CONCURRENCY', 15)
        
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
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100, keepalive_expiry=30.0)
        
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
        self.visited: Set[str] = set()
        self.robots_parser = RobotsParser(self.base_url)

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
        
        # Populate initial frontier according to CRAWL_MODE
        if self.crawl_mode == 'list':
            urls_list = getattr(self.config, 'URLS_LIST', [])
            if not urls_list:
                urls_list = [self.start_url]
            for u in urls_list:
                norm_u = self._normalize_url(u.strip(), self.base_url)
                if norm_u:
                    self.frontier.put_nowait((norm_u, 0, None))
        elif self.crawl_mode == 'sitemap':
            start_norm = self._normalize_url(self.start_url, self.base_url)
            self.frontier.put_nowait((start_norm, 0, None))
            await self.robots_parser.fetch_and_parse(self.client)
            sitemaps = self.robots_parser.get_sitemaps()
            if not sitemaps:
                sitemaps = [urljoin(self.base_url, "/sitemap.xml")]
            sitemap_parser = SitemapParser(self.client)
            for sm in sitemaps:
                await sitemap_parser.fetch_and_parse(sm)
            sm_urls = sitemap_parser.get_all_urls()
            for sm_url in sm_urls:
                norm_url = self._normalize_url(sm_url.url, self.base_url)
                if norm_url != start_norm and self._should_crawl(norm_url, 0):
                    self.frontier.put_nowait((norm_url, 0, self.start_url))
        else:
            # Spider mode: enqueue seed start_norm first so it is crawled first
            start_norm = self._normalize_url(self.start_url, self.base_url)
            self.frontier.put_nowait((start_norm, 0, None))
            await self.robots_parser.fetch_and_parse(self.client)
            sitemaps = self.robots_parser.get_sitemaps()
            if not sitemaps:
                sitemaps = [urljoin(self.base_url, "/sitemap.xml")]
            sitemap_parser = SitemapParser(self.client)
            for sm in sitemaps:
                await sitemap_parser.fetch_and_parse(sm)
            sm_urls = sitemap_parser.get_all_urls()
            for sm_url in sm_urls:
                norm_url = self._normalize_url(sm_url.url, self.base_url)
                if norm_url != start_norm and self._should_crawl(norm_url, 0):
                    self.frontier.put_nowait((norm_url, 1, self.start_url))

        pages_crawled = 0
        
        async def worker():
            nonlocal pages_crawled
            idle_cycles = 0
            max_idle = 30  # Exit after 3 seconds of continuous empty queue (30 * 0.1s)
            while True:
                if pages_crawled >= self.max_pages:
                    break
                try:
                    item = await asyncio.wait_for(self.frontier.get(), timeout=0.5)
                    idle_cycles = 0
                except asyncio.TimeoutError:
                    idle_cycles += 1
                    if idle_cycles >= 6:  # 3 seconds with no new URLs
                        break
                    continue

                if len(item) == 3:
                    url, depth, parent_url = item
                else:
                    url, depth = item[0], item[1]
                    parent_url = None

                if url in self.visited:
                    self.frontier.task_done()
                    continue

                self.visited.add(url)

                async with self.semaphore:
                    try:
                        pages_crawled += 1
                        page_resp = await self._fetch_page(url)

                        if page_resp and "text/html" in page_resp.content_type:
                            raw_hash = hashlib.md5(page_resp.html.encode("utf-8")).hexdigest()
                            page_resp.raw_html_hash = raw_hash
                            rendered_hash = raw_hash

                            needs_js = await self._detect_js_rendering_needed(page_resp.html)
                            if needs_js and getattr(self.config, 'JS_RENDER_ENABLED', True):
                                rendered = await self._fetch_with_playwright(url)
                                if rendered:
                                    rendered_hash = hashlib.md5(rendered.encode("utf-8")).hexdigest()
                                    page_resp.rendered_html_hash = rendered_hash
                                    page_resp.html = rendered

                            parsed = await self._parse_page(page_resp)

                            is_indexable = True
                            if parsed.meta_robots and 'noindex' in parsed.meta_robots.lower():
                                is_indexable = False

                            import json as _json
                            mime_val = page_resp.content_type.split(';')[0].strip() if page_resp.content_type else 'text/html'
                            page_id = await self.database.add_page(
                                audit_id,
                                url=page_resp.final_url,
                                status_code=page_resp.status_code,
                                content_type=page_resp.content_type,
                                response_time_ms=page_resp.response_time_ms,
                                html_size=len(page_resp.html),
                                word_count=parsed.word_count,
                                title=parsed.title,
                                meta_description=parsed.meta_description,
                                h1=parsed.h1_h6.get('h1', [''])[0] if parsed.h1_h6.get('h1') else None,
                                canonical_url=parsed.canonical,
                                viewport=parsed.viewport,
                                is_indexable=is_indexable,
                                crawl_depth=depth,
                                parent_url=parent_url,
                                language=parsed.language,
                                robots_meta=parsed.meta_robots,
                                mime_type=mime_val,
                                redirect_url=page_resp.final_url if page_resp.final_url != url else None,
                                redirect_chain=_json.dumps(page_resp.redirect_chain) if page_resp.redirect_chain else None,
                                content_hash=parsed.content_hash,
                                created_at=datetime.utcnow().isoformat()
                            )

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

                                # Add internal URLs to frontier if in spider mode
                                if is_internal and self.crawl_mode == 'spider' and self._should_crawl(abs_href, depth + 1):
                                    self.frontier.put_nowait((abs_href, depth + 1, page_resp.final_url))

                            if links_batch:
                                await self.database.add_links_batch(links_batch)

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
                                    sd_parsed = _json.loads(sd)
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
                                except _json.JSONDecodeError:
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

                        elif page_resp:
                            await self.database.add_page(
                                audit_id,
                                url=page_resp.final_url,
                                status_code=page_resp.status_code,
                                content_type=page_resp.content_type,
                                response_time_ms=page_resp.response_time_ms,
                                html_size=0,
                                word_count=0,
                                created_at=datetime.utcnow().isoformat()
                            )

                        if self.progress_callback:
                            if asyncio.iscoroutinefunction(self.progress_callback):
                                await self.progress_callback({"crawled": pages_crawled, "total": self.max_pages, "url": url})
                            else:
                                self.progress_callback({"crawled": pages_crawled, "total": self.max_pages, "url": url})

                        # Periodic database flush (batch commits for speed)
                        if pages_crawled % 10 == 0:
                            await self.database.flush()

                        if self.crawl_delay > 0:
                            await asyncio.sleep(self.crawl_delay)

                    except Exception as e:
                        logger.error(f"Error processing {url}: {e}", exc_info=True)
                    finally:
                        self.frontier.task_done()

        num_workers = getattr(self.config, 'CRAWL_CONCURRENCY', 15)
        workers = [asyncio.create_task(worker()) for _ in range(num_workers)]

        # Wait for all workers to finish naturally
        await asyncio.gather(*workers, return_exceptions=True)

        await self.client.aclose()

        # Final flush of any pending writes
        await self.database.flush()

        await self.database.update_audit(
            audit_id,
            status='analyzing',
            completed_at=datetime.utcnow().isoformat(),
            total_pages=pages_crawled
        )

        return audit_id

    async def _fetch_page(self, url: str) -> Optional[PageResponse]:
        if not self.robots_parser.is_allowed(url, self.user_agent):
            logger.info(f"Blocked by robots.txt: {url}")
            return None
            
        start_time = time.time()
        try:
            resp = await self.client.get(url)
            elapsed_ms = (time.time() - start_time) * 1000
            
            chain = [str(r.url) for r in resp.history] if resp.history else []
            
            return PageResponse(
                url=url,
                final_url=str(resp.url),
                status_code=resp.status_code,
                headers=dict(resp.headers),
                html=resp.text,
                response_time_ms=elapsed_ms,
                content_type=resp.headers.get("content-type", ""),
                redirect_chain=chain
            )
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {url}: {e}")
            return None

    async def _parse_page(self, page_response: PageResponse) -> ParsedPage:
        soup = BeautifulSoup(page_response.html, "lxml")
        parsed = ParsedPage()
        
        title_tag = soup.find("title")
        parsed.title = title_tag.text.strip() if title_tag else None
        
        desc_tag = soup.find("meta", attrs={"name": "description"})
        parsed.meta_description = desc_tag.get("content", "").strip() if desc_tag else None
        
        robots_tag = soup.find("meta", attrs={"name": "robots"})
        parsed.meta_robots = robots_tag.get("content", "").strip() if robots_tag else None
        
        canonical_tag = soup.find("link", attrs={"rel": "canonical"})
        parsed.canonical = canonical_tag.get("href", "").strip() if canonical_tag else None
        
        vp_tag = soup.find("meta", attrs={"name": "viewport"})
        parsed.viewport = vp_tag.get("content", "").strip() if vp_tag else None
        
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
            
        text_content = soup.get_text(separator=" ")
        words = [w for w in text_content.split() if w.strip()]
        parsed.word_count = len(words)
        parsed.content_hash = hashlib.md5(" ".join(words).encode("utf-8")).hexdigest()
        
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
            import re
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
        return d1 == d2

    def _should_crawl(self, url: str, depth: int = 0) -> bool:
        if not self._is_internal_url(url):
            return False
        if url in self.visited:
            return False
            
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

    async def _fetch_with_playwright(self, url: str) -> str:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle")
                content = await page.content()
                await browser.close()
                return content
        except ImportError:
            logger.warning("Playwright not installed, skipping JS rendering.")
            return ""
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return ""
