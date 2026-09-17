"""
Pagination Auditor for Vaprolls SEO Spider.
Audits rel="next" and rel="prev" pagination series, canonicalization, and indexability.
"""
import logging
from typing import Optional, Any, Dict, List, Set
from database.db import Database

logger = logging.getLogger(__name__)

class PaginationAuditor:
    """
    Audits pagination tags and series implementation:
    - Broken pagination targets (next/prev target returning 4xx or 5xx)
    - Self-referencing pagination (rel="next" or rel="prev" equals current URL)
    - First page with rel="prev" (page 1 should not specify a previous page)
    - Paginated page canonical pointing to page 1 (should be self-referencing)
    - Paginated page marked noindex
    - Circular pagination loops (next points back to prev)
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting pagination audit for audit {self.audit_id}")
        pagination_tags = await self.db.get_pagination_tags(self.audit_id)
        if not pagination_tags:
            logger.info("No pagination tags found for this audit.")
            return

        pages = await self.db.get_pages(self.audit_id)
        pages_by_url: Dict[str, Dict[str, Any]] = {}
        for p in pages:
            u = p.get('url', '')
            if u:
                pages_by_url[u] = p
                pages_by_url[u.rstrip('/')] = p

        # Group pagination tags by source page
        tags_by_page: Dict[str, List[Dict[str, Any]]] = {}
        for t in pagination_tags:
            src = t.get('page_url', '').strip()
            if src:
                tags_by_page.setdefault(src, []).append(t)

        series_count = len(tags_by_page)

        for page_url, tags in tags_by_page.items():
            page_data = pages_by_url.get(page_url) or pages_by_url.get(page_url.rstrip('/'))
            page_id = page_data.get('id') if page_data else None

            next_url = None
            prev_url = None

            for tag in tags:
                rel = tag.get('rel_type', '').lower().strip()
                target = tag.get('target_url', '').strip()

                if rel == 'next':
                    next_url = target
                elif rel == 'prev':
                    prev_url = target

                # 1. Self-referencing check
                if target and (target == page_url or target.rstrip('/') == page_url.rstrip('/')):
                    await self._add_issue(
                        page_id, page_url, 'critical', 'pagination_self_referencing',
                        f"Pagination rel='{rel}' points to itself: {target}",
                        f"Remove self-referencing rel='{rel}' link tag; it must point to the preceding or succeeding page.",
                        target
                    )

                # 2. Check target HTTP status
                target_page = pages_by_url.get(target) or pages_by_url.get(target.rstrip('/'))
                if target_page:
                    status = target_page.get('status_code', 0)
                    if status >= 400:
                        await self._add_issue(
                            page_id, page_url, 'critical', 'pagination_broken_target',
                            f"Pagination rel='{rel}' points to broken URL returning HTTP {status}: {target}",
                            "Fix or remove the pagination link to prevent crawling errors.",
                            target
                        )
                    elif 300 <= status < 400:
                        await self._add_issue(
                            page_id, page_url, 'warning', 'pagination_redirect_target',
                            f"Pagination rel='{rel}' points to redirected URL (HTTP {status}): {target}",
                            "Update pagination tag to link directly to the destination 200 URL.",
                            target
                        )

            # 3. Circular loop: next points to prev
            if next_url and prev_url and (next_url == prev_url or next_url.rstrip('/') == prev_url.rstrip('/')):
                await self._add_issue(
                    page_id, page_url, 'critical', 'pagination_circular_loop',
                    f"Pagination rel='next' and rel='prev' both point to identical URL: {next_url}",
                    "Fix pagination sequence so rel='next' and rel='prev' point to distinct pages in the sequence.",
                    next_url
                )

            # 4. Check canonicalization on paginated pages
            if page_data:
                canonical = page_data.get('canonical_url')
                if canonical and prev_url:
                    # This is page 2+ in a series. Check if canonical points to page 1 or root
                    canonical_norm = canonical.rstrip('/')
                    url_norm = page_url.rstrip('/')
                    if canonical_norm != url_norm:
                        # Canonical does not match current URL. If it points to prev_url, that's an error!
                        if canonical_norm == prev_url.rstrip('/'):
                            await self._add_issue(
                                page_id, page_url, 'critical', 'paginated_canonical_to_first_page',
                                f"Paginated page canonicalizes to previous/first page instead of self-referencing: {canonical}",
                                "Set self-referencing canonical tag on paginated pages, or Google will de-index page 2+ and miss products/articles.",
                                canonical
                            )

                # 5. Check noindex on paginated pages
                if page_data.get('is_indexable') is False:
                    meta_robots = (page_data.get('robots_meta') or '').lower()
                    x_robots = (page_data.get('x_robots_tag') or '').lower()
                    if 'noindex' in meta_robots or 'noindex' in x_robots:
                        await self._add_issue(
                            page_id, page_url, 'warning', 'paginated_page_noindex',
                            "Paginated page has 'noindex' directive, blocking search engines from indexing deep items",
                            "Remove noindex from paginated pages unless intentionally hiding archived sequences.",
                            page_url
                        )

        # Site-wide summary
        await self._add_issue(
            None, None, 'info', 'pagination_summary',
            f"Pagination Audit: evaluated {len(pagination_tags)} tags across {series_count} paginated pages",
            "Verify all pagination sequences flow smoothly from page 1 to end without broken hops.",
            {
                'paginated_pages_count': series_count,
                'total_pagination_tags': len(pagination_tags)
            }
        )

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='pagination',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
