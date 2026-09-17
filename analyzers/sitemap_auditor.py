"""
Sitemap Auditor for Vaprolls SEO Spider.
Cross-references crawled pages against XML sitemap entries to detect SEO anomalies.
"""
import logging
from typing import Optional, Any, Dict, List, Set
from database.db import Database

logger = logging.getLogger(__name__)

class SitemapAuditor:
    """
    Validates XML Sitemaps against crawled pages:
    - URLs in sitemap returning non-200 status (404, 500, etc.)
    - Redirected URLs present in sitemap (should only contain canonical 200 URLs)
    - Noindex pages present in sitemap (contradictory directives)
    - Orphan sitemap URLs (in sitemap but no internal links point to them)
    - Missing pages: indexable 200 pages that are absent from sitemaps
    - Sitemap size & URL limits (> 50,000 URLs or > 50MB)
    - Sitemap coverage ratio
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting sitemap audit for audit {self.audit_id}")
        sitemap_entries = await self.db.get_sitemap_entries(self.audit_id)
        pages = await self.db.get_pages(self.audit_id)

        if not sitemap_entries:
            logger.info("No sitemap entries found for this audit.")
            await self._add_issue(
                None, None, 'warning', 'no_sitemaps_found',
                "No XML sitemap entries discovered or processed",
                "Ensure your XML sitemap is reachable at /sitemap.xml and listed in robots.txt.",
                None
            )
            return

        # Map pages by URL and normalized URL
        pages_by_url: Dict[str, Dict[str, Any]] = {}
        for p in pages:
            u = p.get('url', '')
            if u:
                pages_by_url[u] = p
                pages_by_url[u.rstrip('/')] = p

        sitemap_urls: Set[str] = set()
        sitemaps_count: Dict[str, int] = {}
        non_200_count = 0
        redirect_count = 0
        noindex_count = 0
        orphan_count = 0

        for entry in sitemap_entries:
            page_url = entry.get('page_url', '').strip()
            sitemap_loc = entry.get('sitemap_url', 'default')
            if not page_url:
                continue

            sitemap_urls.add(page_url)
            sitemaps_count[sitemap_loc] = sitemaps_count.get(sitemap_loc, 0) + 1

            matched_page = pages_by_url.get(page_url) or pages_by_url.get(page_url.rstrip('/'))
            if matched_page:
                status = matched_page.get('status_code', 0)
                page_id = matched_page.get('id')

                # 1. Non-200 in sitemap
                if status >= 400:
                    non_200_count += 1
                    await self._add_issue(
                        page_id, page_url, 'critical', 'sitemap_url_broken',
                        f"Sitemap URL returns HTTP {status}",
                        "Remove broken or 404/500 URLs from your XML sitemap.",
                        page_url
                    )
                elif 300 <= status < 400:
                    redirect_count += 1
                    await self._add_issue(
                        page_id, page_url, 'warning', 'sitemap_url_redirect',
                        f"Sitemap URL returns HTTP {status} redirect to {matched_page.get('redirect_url')}",
                        "Update sitemap entries to point directly to destination 200 OK canonical URLs.",
                        page_url
                    )

                # 2. Noindex in sitemap
                if matched_page.get('is_indexable') is False:
                    noindex_count += 1
                    await self._add_issue(
                        page_id, page_url, 'warning', 'sitemap_url_noindex',
                        "Non-indexable (noindex or blocked) URL included in sitemap",
                        "Remove non-indexable URLs from XML sitemap to prevent confusing search engine crawlers.",
                        page_url
                    )

                # 3. Orphan sitemap URL (in sitemap but 0 internal inlinks)
                inlinks = matched_page.get('unique_inlinks', 0)
                if inlinks == 0 and matched_page.get('crawl_depth', 0) > 0:
                    orphan_count += 1
                    await self._add_issue(
                        page_id, page_url, 'warning', 'sitemap_orphan_url',
                        "Sitemap URL has zero internal inlinks (orphan page)",
                        "Add internal navigation links to this page so users and crawlers can discover it naturally.",
                        page_url
                    )

        # 4. Check sitemap URL counts against 50,000 limit
        for sm_url, count in sitemaps_count.items():
            if count > 50000:
                await self._add_issue(
                    None, sm_url, 'critical', 'sitemap_exceeds_url_limit',
                    f"Sitemap {sm_url} contains {count} URLs (exceeds Google limit of 50,000)",
                    "Split sitemap into multiple smaller sitemaps using a Sitemap Index file.",
                    count
                )

        # 5. Missing indexable pages (in crawl but not in sitemap)
        indexable_pages = [
            p for p in pages 
            if p.get('status_code') == 200 
            and p.get('is_indexable') is True 
            and 'text/html' in (p.get('content_type') or '').lower()
        ]
        
        missing_from_sitemap = []
        for p in indexable_pages:
            u = p.get('url', '')
            if u not in sitemap_urls and u.rstrip('/') not in sitemap_urls:
                missing_from_sitemap.append(u)

        if missing_from_sitemap:
            sample_missing = missing_from_sitemap[:10]
            await self._add_issue(
                None, None, 'warning', 'pages_missing_from_sitemap',
                f"{len(missing_from_sitemap)} indexable pages are missing from XML sitemaps",
                "Ensure all valuable canonical indexable pages are listed in your XML sitemap.",
                sample_missing
            )

        # 6. Sitemap Coverage Ratio
        total_indexable = len(indexable_pages)
        if total_indexable > 0:
            covered_count = total_indexable - len(missing_from_sitemap)
            coverage_pct = round((covered_count / total_indexable) * 100, 1)
            severity = 'info' if coverage_pct >= 90 else ('warning' if coverage_pct >= 70 else 'critical')
            await self._add_issue(
                None, None, severity, 'sitemap_coverage',
                f"Sitemap Coverage: {coverage_pct}% ({covered_count}/{total_indexable} indexable pages in sitemap)",
                "Improve sitemap generation automation to achieve >95% indexable coverage.",
                {
                    'coverage_pct': coverage_pct,
                    'in_sitemap_and_crawl': covered_count,
                    'total_indexable_crawled': total_indexable,
                    'missing_from_sitemap_count': len(missing_from_sitemap),
                    'total_sitemap_entries': len(sitemap_entries),
                    'non_200_in_sitemap': non_200_count,
                    'redirects_in_sitemap': redirect_count,
                    'noindex_in_sitemap': noindex_count,
                    'orphans_in_sitemap': orphan_count
                }
            )

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='sitemaps',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
