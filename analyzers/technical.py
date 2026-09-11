import logging
import json
import urllib.parse
from typing import Dict, Any, List, Optional
from database.db import Database

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting technical analysis for audit {self.audit_id}")
        
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            logger.warning(f"No pages found for audit {self.audit_id}")
            return

        for page in pages:
            await self.check_http_status(page)
            await self.check_redirects(page)
            await self.check_response_time(page)
            await self.check_canonical(page, pages)
            await self.check_meta_robots(page)
            await self.check_indexability(page)
            await self.check_url_structure(page)
            await self.check_crawl_depth(page)

        await self.check_orphan_pages(pages)
        await self.check_site_wide_5xx(pages)
        await self.check_site_wide_redirect_chains(pages)
        await self.check_mixed_http_https(pages)
        await self.check_www_consistency(pages)
        await self.check_trailing_slash_consistency(pages)
        await self.check_robots_blocked_but_linked(pages)

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='technical',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )

    # --- Per-Page Checks ---

    async def check_http_status(self, page: Dict[str, Any]):
        status = page.get('status_code')
        url = page.get('url')
        page_id = page.get('id')
        
        if not status:
            return

        if 400 <= status < 500:
            await self._add_issue(page_id, url, 'critical', '4xx_error', f"Page returned 4xx error ({status})", "Fix the broken link or restore the page.", status)
        elif status >= 500:
            await self._add_issue(page_id, url, 'critical', '5xx_error', f"Page returned 5xx error ({status})", "Check server logs to fix the server error.", status)
        elif 300 <= status < 400:
            redirect_url = page.get('redirect_url', 'Unknown target')
            await self._add_issue(page_id, url, 'info', '3xx_redirect', f"Page redirects to {redirect_url} ({status})", "Ensure this redirect is intentional.", redirect_url)
        elif status != 200:
            await self._add_issue(page_id, url, 'warning', 'non_200_status', f"Page returned non-200 status ({status})", "Investigate the status code.", status)

    async def check_redirects(self, page: Dict[str, Any]):
        url = page.get('url')
        page_id = page.get('id')
        
        chain_raw = page.get('redirect_chain')
        if not chain_raw:
            return
            
        try:
            chain = json.loads(chain_raw) if isinstance(chain_raw, str) else chain_raw
        except json.JSONDecodeError:
            chain = []

        if isinstance(chain, list) and len(chain) > 1:
            if len(chain) > 3:
                await self._add_issue(page_id, url, 'critical', 'long_redirect_chain', "Redirect chain has more than 3 hops", "Update links to point directly to the final destination.", chain)
            else:
                await self._add_issue(page_id, url, 'warning', 'redirect_chain', "Redirect chain detected", "Update links to point directly to the final destination.", chain)
                
            # Check for loops (simplified: if url appears more than once in the chain)
            if len(set(chain)) < len(chain):
                await self._add_issue(page_id, url, 'critical', 'redirect_loop', "Redirect loop detected", "Fix the server configuration causing an infinite redirect loop.", chain)

    async def check_response_time(self, page: Dict[str, Any]):
        ttfb = page.get('response_time')
        url = page.get('url')
        page_id = page.get('id')
        
        if ttfb is not None:
            # Assuming ttfb is in ms, if it's seconds, convert or handle. Let's assume ms.
            if ttfb > 3000:
                await self._add_issue(page_id, url, 'critical', 'very_slow_response', "Very slow server response (TTFB > 3000ms)", "Optimize server response time.", ttfb)
            elif ttfb > 1000:
                await self._add_issue(page_id, url, 'warning', 'slow_response', "Slow server response (TTFB > 1000ms)", "Optimize server response time.", ttfb)

    async def check_canonical(self, page: Dict[str, Any], all_pages: List[Dict[str, Any]]):
        url = page.get('url')
        page_id = page.get('id')
        canonical = page.get('canonical_url')
        
        if not canonical:
            await self._add_issue(page_id, url, 'warning', 'missing_canonical', "Missing canonical tag", "Add a self-referencing canonical tag.", None)
            return

        if canonical != url:
            await self._add_issue(page_id, url, 'info', 'different_canonical', "Canonical points to a different URL", "Verify if the canonical tag is intentionally pointing to another page.", canonical)
            
            canonical_page = next((p for p in all_pages if p.get('url') == canonical), None)
            if canonical_page:
                if not canonical_page.get('is_indexable', True):
                    await self._add_issue(page_id, url, 'critical', 'canonical_non_indexable', "Canonical points to a non-indexable page", "Change the canonical tag to point to an indexable page.", canonical)
                
                status = canonical_page.get('status_code')
                if status and status != 200:
                    await self._add_issue(page_id, url, 'critical', 'canonical_non_200', f"Canonical URL returns non-200 status ({status})", "Ensure the canonical URL returns a 200 OK status.", status)

    async def check_meta_robots(self, page: Dict[str, Any]):
        url = page.get('url')
        page_id = page.get('id')
        is_indexable = page.get('is_indexable', True)
        in_sitemap = page.get('in_sitemap', False)
        
        if not is_indexable:
            if in_sitemap:
                await self._add_issue(page_id, url, 'warning', 'noindex_in_sitemap', "Page has noindex but is in sitemap", "Remove noindexed pages from the XML sitemap.", None)
            else:
                await self._add_issue(page_id, url, 'info', 'page_noindex', "Page has noindex", "Ensure this page is intentionally excluded from indexing.", None)

    async def check_indexability(self, page: Dict[str, Any]):
        url = page.get('url')
        page_id = page.get('id')
        is_indexable = page.get('is_indexable', True)
        is_important = page.get('is_important', False)
        
        if not is_indexable:
            links = await self.db.get_links(self.audit_id, is_internal=True)
            incoming_links = [link for link in links if link.get('target_url') == url]
            if incoming_links:
                await self._add_issue(page_id, url, 'warning', 'noindex_internal_links', "Non-indexable page receiving internal links", "Remove internal links to non-indexable pages to preserve crawl budget.", None)
                
            if is_important:
                await self._add_issue(page_id, url, 'critical', 'important_page_noindex', "Important page not indexable", "Make the page indexable by removing the noindex tag or robots.txt block.", None)

    async def check_url_structure(self, page: Dict[str, Any]):
        url = page.get('url')
        if not url: return
        page_id = page.get('id')
        
        if len(url) > 115:
            await self._add_issue(page_id, url, 'warning', 'long_url', "URL length > 115 characters", "Shorten the URL to improve UX and shareability.", len(url))
            
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        
        if any(c.isupper() for c in path):
            await self._add_issue(page_id, url, 'warning', 'uppercase_url', "URL contains uppercase letters", "Use lowercase letters in URLs to avoid duplicate content issues.", path)
            
        if '_' in path:
            await self._add_issue(page_id, url, 'info', 'underscore_in_url', "URL contains underscores instead of hyphens", "Use hyphens to separate words in URLs.", path)
            
        if any(ord(c) > 127 or c in ' %$&+,;=?' for c in urllib.parse.unquote(path)):
            await self._add_issue(page_id, url, 'warning', 'special_chars_url', "URL contains special characters", "Remove special characters from URLs.", path)
            
        params = urllib.parse.parse_qs(parsed.query)
        if len(params) > 2:
            await self._add_issue(page_id, url, 'warning', 'excessive_url_params', "URL has excessive parameters (> 2)", "Reduce the number of URL parameters.", len(params))
            
        depth = len([p for p in path.split('/') if p])
        if depth > 5:
            await self._add_issue(page_id, url, 'info', 'excessive_path_depth', "URL has excessive path depth (> 5 levels)", "Flatten the URL structure.", depth)

    async def check_crawl_depth(self, page: Dict[str, Any]):
        url = page.get('url')
        page_id = page.get('id')
        depth = page.get('crawl_depth')
        
        if depth is not None:
            if depth > 5:
                await self._add_issue(page_id, url, 'critical', 'deep_crawl_depth', "Page very deep — may not be crawled by search engines", "Link to this page from pages closer to the homepage.", depth)
            elif depth > 3:
                await self._add_issue(page_id, url, 'warning', 'high_crawl_depth', "Page too deep in site structure", "Improve internal linking to reduce crawl depth.", depth)

    # --- Site-Wide Checks ---

    async def check_orphan_pages(self, pages: List[Dict[str, Any]]):
        links = await self.db.get_links(self.audit_id, is_internal=True)
        linked_urls = {link.get('target_url') for link in links if link.get('target_url')}
        
        for page in pages:
            url = page.get('url')
            if not url: continue
            
            depth = page.get('crawl_depth')
            if depth is None or url not in linked_urls:
                # If depth is 0 it's likely the start URL, don't flag as orphan if it is the seed
                if depth == 0:
                    continue
                await self._add_issue(page.get('id'), url, 'warning', 'orphan_page', "Page has no internal links pointing to it", "Add internal links to this page.", None)

    async def check_site_wide_5xx(self, pages: List[Dict[str, Any]]):
        count_5xx = sum(1 for p in pages if p.get('status_code') and p.get('status_code') >= 500)
        if count_5xx > 0:
            await self._add_issue(None, None, 'critical', 'site_wide_5xx', f"Site has {count_5xx} pages returning 5xx errors", "Investigate server stability and fix 5xx errors immediately.", count_5xx)

    async def check_site_wide_redirect_chains(self, pages: List[Dict[str, Any]]):
        chain_count = 0
        for page in pages:
            chain_raw = page.get('redirect_chain')
            if chain_raw:
                try:
                    chain = json.loads(chain_raw) if isinstance(chain_raw, str) else chain_raw
                    if isinstance(chain, list) and len(chain) > 1:
                        chain_count += 1
                except json.JSONDecodeError:
                    pass
        if chain_count > 0:
            await self._add_issue(None, None, 'warning', 'site_wide_redirect_chains', f"Site has {chain_count} pages with redirect chains", "Resolve redirect chains to improve performance.", chain_count)

    async def check_mixed_http_https(self, pages: List[Dict[str, Any]]):
        schemes = set()
        for p in pages:
            url = p.get('url')
            if url:
                schemes.add(urllib.parse.urlparse(url).scheme)
        if 'http' in schemes and 'https' in schemes:
            await self._add_issue(None, None, 'critical', 'mixed_http_https', "Site has mixed HTTP and HTTPS URLs", "Migrate all pages to HTTPS and enforce HTTPS redirects.", list(schemes))

    async def check_www_consistency(self, pages: List[Dict[str, Any]]):
        has_www = False
        has_non_www = False
        for p in pages:
            url = p.get('url')
            if url:
                netloc = urllib.parse.urlparse(url).netloc
                if netloc.startswith('www.'):
                    has_www = True
                else:
                    has_non_www = True
                    
        if has_www and has_non_www:
            await self._add_issue(None, None, 'warning', 'www_inconsistency', "Inconsistent usage of www and non-www URLs", "Standardize on either www or non-www and implement 301 redirects.", None)

    async def check_trailing_slash_consistency(self, pages: List[Dict[str, Any]]):
        has_slash = False
        has_no_slash = False
        for p in pages:
            url = p.get('url')
            if url:
                path = urllib.parse.urlparse(url).path
                if path != '/' and path.endswith('/'):
                    has_slash = True
                elif path != '/' and not path.endswith('/'):
                    has_no_slash = True
                    
        if has_slash and has_no_slash:
            await self._add_issue(None, None, 'warning', 'trailing_slash_inconsistency', "Inconsistent usage of trailing slashes", "Standardize trailing slash usage and implement 301 redirects.", None)

    async def check_robots_blocked_but_linked(self, pages: List[Dict[str, Any]]):
        links = await self.db.get_links(self.audit_id, is_internal=True)
        linked_targets = {link.get('target_url') for link in links if link.get('target_url')}
        
        for p in pages:
            url = p.get('url')
            # If a page is marked as not indexable via robots.txt and is linked internally
            # We assume is_indexable=False can mean blocked by robots.txt or meta robots.
            # To specifically check robots.txt, we might need a specific field, but we can fall back to is_indexable.
            if not p.get('is_indexable', True) and url in linked_targets:
                # To be precise, check if it's explicitly robots blocked if the field exists, 
                # else we already flag non-indexable receiving internal links in check_indexability.
                # If we need a site-wide summary or if 'blocked_by_robots' is a field:
                is_blocked = p.get('blocked_by_robots', False)
                if is_blocked:
                    await self._add_issue(None, None, 'warning', 'robots_blocked_linked', f"Page blocked by robots.txt is linked internally: {url}", "Remove internal links to pages blocked by robots.txt.", url)

