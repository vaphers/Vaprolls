"""
Robots.txt Auditor for Vaprolls SEO Spider.
Audits robots.txt syntax, site-wide crawling rules, blocked internal links, and sitemap directives.
"""
import logging
from typing import Optional, Any, Dict, List, Set
from urllib.parse import urlparse, urljoin
import httpx

from database.db import Database
from crawler.robots import RobotsParser

logger = logging.getLogger(__name__)

class RobotsAuditor:
    """
    Validates robots.txt compliance and SEO impact:
    - Robots.txt availability and HTTP status code
    - Robots.txt file size (< 500KB Google limit)
    - Full site block detection (Disallow: /)
    - Syntax error and malformed line detection
    - Crawl-delay directives (ignored by Googlebot, supported by Bing)
    - Missing Sitemap directives in robots.txt
    - Blocked internally-linked pages (crawlers cannot reach links on these pages)
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting robots.txt audit for audit {self.audit_id}")
        audit = await self.db.get_audit(self.audit_id)
        if not audit:
            return

        start_url = audit.get('url', '')
        if not start_url:
            return

        parsed_start = urlparse(start_url)
        base_url = f"{parsed_start.scheme}://{parsed_start.netloc}"
        robots_url = urljoin(base_url, "/robots.txt")

        # 1. Fetch robots.txt
        status_code = 0
        content = ""
        size_bytes = 0
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(robots_url)
                status_code = resp.status_code
                content = resp.text
                size_bytes = len(resp.content)
        except Exception as e:
            logger.warning(f"Could not fetch {robots_url}: {e}")
            await self._add_issue(
                None, robots_url, 'warning', 'robots_txt_fetch_error',
                f"Failed to fetch robots.txt: {e}",
                "Ensure robots.txt is accessible over HTTP/HTTPS with proper server configuration.",
                str(e)
            )
            return

        if status_code != 200:
            severity = 'info' if status_code == 404 else 'warning'
            await self._add_issue(
                None, robots_url, severity, 'robots_txt_missing_or_error',
                f"robots.txt returned HTTP {status_code}",
                "Create a valid robots.txt file at the root of your domain to guide search engine crawlers.",
                status_code
            )
            return

        # 2. File size check (< 500KB)
        if size_bytes > 512000:
            await self._add_issue(
                None, robots_url, 'critical', 'robots_txt_oversized',
                f"robots.txt file size is {size_bytes / 1024:.1f}KB (>500KB Google cutoff)",
                "Reduce robots.txt file size below 500KB. Googlebot truncates robots.txt files exceeding 512KB.",
                size_bytes
            )

        # 3. Analyze content line by line
        lines = content.splitlines()
        has_sitemap = False
        has_full_site_disallow = False
        crawl_delays = []
        malformed_lines = []
        current_agent = None

        KNOWN_DIRECTIVES = {
            'user-agent', 'disallow', 'allow', 'sitemap',
            'crawl-delay', 'host', 'clean-param'
        }

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            if ':' not in stripped:
                malformed_lines.append(f"Line {idx}: {stripped}")
                continue

            parts = stripped.split(':', 1)
            directive = parts[0].strip().lower()
            val = parts[1].strip()

            if directive not in KNOWN_DIRECTIVES:
                malformed_lines.append(f"Line {idx}: Unknown directive '{directive}'")

            if directive == 'user-agent':
                current_agent = val.lower()
            elif directive == 'disallow':
                if val == '/' and current_agent in ('*', 'googlebot'):
                    has_full_site_disallow = True
            elif directive == 'sitemap':
                has_sitemap = True
            elif directive == 'crawl-delay':
                crawl_delays.append(f"Agent {current_agent}: {val}s")

        # Flag full-site disallow
        if has_full_site_disallow:
            await self._add_issue(
                None, robots_url, 'critical', 'robots_txt_full_site_disallowed',
                "robots.txt blocks entire site with 'Disallow: /' for all robots or Googlebot",
                "Remove 'Disallow: /' immediately if the site is intended to be indexed by search engines.",
                "Disallow: /"
            )

        # Flag malformed lines
        if malformed_lines:
            await self._add_issue(
                None, robots_url, 'warning', 'robots_txt_syntax_errors',
                f"robots.txt contains {len(malformed_lines)} invalid or unrecognized directives",
                "Review and correct robots.txt syntax according to the Robots Exclusion Standard.",
                malformed_lines[:10]
            )

        # Flag missing sitemap reference
        if not has_sitemap:
            await self._add_issue(
                None, robots_url, 'info', 'robots_txt_missing_sitemap',
                "robots.txt does not contain a Sitemap directive",
                "Add 'Sitemap: https://yourdomain.com/sitemap.xml' to the bottom of robots.txt for faster crawler discovery.",
                None
            )

        # Flag crawl-delay notice
        if crawl_delays:
            await self._add_issue(
                None, robots_url, 'info', 'robots_txt_crawl_delay_present',
                f"robots.txt specifies crawl-delay ({', '.join(crawl_delays)})",
                "Note that Googlebot ignores Crawl-delay directives; use Google Search Console crawl rate settings instead.",
                crawl_delays
            )

        # 4. Check for blocked internal links
        # Parse robots using RobotsParser
        robots_parser = RobotsParser(start_url)
        await robots_parser.fetch_and_parse()

        links = await self.db.get_links(self.audit_id, is_internal=True)
        checked_targets: Set[str] = set()
        blocked_targets: List[str] = []

        for link in links:
            t_url = link.get('target_url')
            if not t_url or t_url in checked_targets:
                continue
            checked_targets.add(t_url)

            if not robots_parser.is_allowed(t_url, '*'):
                blocked_targets.append(t_url)
                sp_id = link.get('source_page_id')
                s_url = link.get('source_url')
                await self._add_issue(
                    sp_id, s_url, 'warning', 'internally_linked_url_blocked_by_robots',
                    f"Page links to URL blocked by robots.txt: {t_url}",
                    "Update robots.txt or remove the internal link to ensure crawl budget is used efficiently.",
                    t_url
                )

        if blocked_targets:
            await self._add_issue(
                None, None, 'warning', 'site_wide_blocked_internal_urls',
                f"{len(blocked_targets)} unique internally-linked URLs are blocked by robots.txt",
                "Review robots.txt disallow rules against internal navigation.",
                len(blocked_targets)
            )

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='robots',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
