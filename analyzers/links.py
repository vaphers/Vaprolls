import logging
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import httpx

from database.db import Database

logger = logging.getLogger(__name__)

class LinkAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id
        self.status_updates = []
        self.issues_buffer = []

    async def analyze(self):
        """
        Fetches internal links and pages, verifies link targets and status codes,
        detects broken and redirected links, and records actionable SEO issues.
        """
        logger.info(f"Starting LinkAnalyzer for audit {self.audit_id}")

        pages = await self.db.get_pages(self.audit_id)
        links = await self.db.get_links(self.audit_id)

        # Map known page statuses from crawl
        page_status_map: Dict[str, Optional[int]] = {p['url']: p.get('status_code') for p in pages}

        # Identify uncrawled internal target URLs and check them
        uncrawled_internal = set()
        for link in links:
            if link.get('is_internal', True):
                t_url = link.get('target_url')
                if t_url and t_url not in page_status_map:
                    uncrawled_internal.add(t_url)

        if uncrawled_internal:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=False, limits=httpx.Limits(max_connections=30)) as client:
                sem = asyncio.Semaphore(20)
                async def _probe_url(target):
                    async with sem:
                        try:
                            resp = await client.head(target)
                            return target, resp.status_code
                        except Exception:
                            try:
                                resp = await client.get(target)
                                return target, resp.status_code
                            except Exception:
                                return target, 0

                probe_targets = list(uncrawled_internal)[:250]
                results = await asyncio.gather(*[_probe_url(t) for t in probe_targets], return_exceptions=True)
                for res in results:
                    if isinstance(res, tuple):
                        t, sc = res
                        page_status_map[t] = sc

        links_by_source_page_id: Dict[int, List[Dict[str, Any]]] = {}
        incoming_internal_links: Dict[str, int] = {p['url']: 0 for p in pages}

        for link in links:
            # Enforce internal only
            if not link.get('is_internal', True):
                continue

            source_page_id = link['source_page_id']
            if source_page_id not in links_by_source_page_id:
                links_by_source_page_id[source_page_id] = []
            links_by_source_page_id[source_page_id].append(link)

            target_url = link.get('target_url')
            if target_url in incoming_internal_links:
                incoming_internal_links[target_url] += 1

        total_broken_internal = 0
        generic_anchor_texts = {'click here', 'read more', 'learn more', 'here', 'this', 'link', 'website'}

        for page in pages:
            page_id = page['id']
            url = page['url']
            page_links = links_by_source_page_id.get(page_id, [])

            internal_links_count = len(page_links)

            # 1. Pages with no outgoing internal links
            if internal_links_count == 0:
                await self._add_issue(
                    page_id=page_id, url=url, severity='warning', issue_type='no_internal_links',
                    message="This page has no outgoing internal links. Users and crawlers cannot navigate further into your site.",
                    recommendation="Add relevant internal links to other category, service, or article pages."
                )
            # 2. Pages with only 1 internal link
            elif internal_links_count == 1:
                await self._add_issue(
                    page_id=page_id, url=url, severity='info', issue_type='few_internal_links',
                    message="This page has only 1 internal link.",
                    recommendation="Consider adding contextual internal links to improve user journeys and equity distribution."
                )

            # 3. Click depth analysis
            crawl_depth = page.get('crawl_depth')
            if crawl_depth is not None and crawl_depth > 4:
                await self._add_issue(
                    page_id=page_id, url=url, severity='warning', issue_type='excessive_crawl_depth',
                    message=f"Deep click depth: Page is {crawl_depth} clicks away from the homepage.",
                    recommendation="Bring important pages closer to the homepage (maximum 3 clicks deep)."
                )

            # 4. Outgoing Internal Link Target Health & Anchor Text
            empty_anchors = []
            generic_anchors = []

            for link in page_links:
                target_url = link.get('target_url')
                anchor = (link.get('anchor_text') or '').strip()
                nofollow = link.get('nofollow')
                link_id = link.get('id')

                status_code = page_status_map.get(target_url)
                if status_code is None:
                    status_code = 200

                is_broken = False
                if status_code and (status_code >= 400 or status_code == 0):
                    is_broken = True
                    total_broken_internal += 1
                    await self._add_issue(
                        page_id=page_id, url=url, severity='critical', issue_type='broken_internal_link',
                        message=f"Broken internal link to {target_url} (HTTP {status_code or 'Timeout'}). Anchor: '{anchor or '[No Anchor]'}'.",
                        recommendation=f"Update or remove this broken hyperlink on {url}.",
                        element=target_url
                    )
                elif status_code in (301, 302, 307, 308):
                    await self._add_issue(
                        page_id=page_id, url=url, severity='warning', issue_type='redirected_internal_link',
                        message=f"Internal link points to a redirected URL ({target_url}, HTTP {status_code}). Anchor: '{anchor or '[No Anchor]'}'.",
                        recommendation="Update the internal link to point directly to the final 200 OK destination URL.",
                        element=target_url
                    )

                # Update database link record with actual status and broken flag
                if link_id:
                    self.status_updates.append((status_code, is_broken, link_id))
                    if len(self.status_updates) >= 500:
                        await self.db.update_links_status_batch(self.status_updates)
                        self.status_updates = []

                # Internal nofollow links
                if nofollow:
                    await self._add_issue(
                        page_id=page_id, url=url, severity='info', issue_type='nofollow_internal_link',
                        message=f"Internal link to {target_url} has nofollow attribute. This wastes PageRank link equity.",
                        recommendation="Remove the rel='nofollow' attribute from internal navigation and contextual links.",
                        element=target_url
                    )

                # Collect anchor text diagnostics
                if not anchor:
                    empty_anchors.append(target_url)
                else:
                    anchor_lower = anchor.lower()
                    if anchor_lower in generic_anchor_texts:
                        generic_anchors.append(f"{target_url} ('{anchor}')")
                    elif len(anchor) > 100:
                        await self._add_issue(
                            page_id=page_id, url=url, severity='info', issue_type='long_anchor_text',
                            message=f"Link has excessively long anchor text ({len(anchor)} characters).",
                            recommendation="Keep anchor texts concise and focused (under 100 characters).",
                            element=anchor[:90] + '...'
                        )

            # Per-page aggregated anchor issues (fast, concise, and eliminates thousands of duplicate rows)
            if empty_anchors:
                sample_preview = ", ".join(empty_anchors[:4])
                if len(empty_anchors) > 4:
                    sample_preview += f" and {len(empty_anchors) - 4} more"
                await self._add_issue(
                    page_id=page_id, url=url, severity='warning', issue_type='empty_anchor_text',
                    message=f"Page has {len(empty_anchors)} internal link(s) with empty anchor text.",
                    recommendation="Provide descriptive, accessible anchor text explaining where links lead.",
                    element=sample_preview
                )

            if generic_anchors:
                sample_preview = ", ".join(generic_anchors[:4])
                if len(generic_anchors) > 4:
                    sample_preview += f" and {len(generic_anchors) - 4} more"
                await self._add_issue(
                    page_id=page_id, url=url, severity='warning', issue_type='generic_anchor_text',
                    message=f"Page has {len(generic_anchors)} link(s) using generic anchor text (e.g. 'click here', 'read more').",
                    recommendation="Replace generic text with keyword-rich, contextual descriptions.",
                    element=sample_preview
                )

        # Site-Wide Internal Link Hygiene
        for page in pages:
            url = page['url']
            inc_links = incoming_internal_links.get(url, 0)
            
            # Orphan pages (0 incoming internal links)
            if inc_links == 0:
                await self._add_issue(
                    page_id=page['id'], url=url, severity='critical', issue_type='orphan_page',
                    message="Orphan page: has 0 incoming internal links from other crawled pages.",
                    recommendation="Link to this page from top navigation, parent category, or related content."
                )
            elif inc_links < 3:
                await self._add_issue(
                    page_id=page['id'], url=url, severity='info', issue_type='few_incoming_links',
                    message=f"Page has very few incoming internal links ({inc_links}).",
                    recommendation="Add more internal links pointing to this page to boost its crawl frequency and index authority."
                )

        # Compute and persist unique inlinks, outlinks, and link score
        inlinks_map: Dict[str, set] = {p['url']: set() for p in pages}
        internal_outlinks_map: Dict[int, set] = {p['id']: set() for p in pages}
        external_outlinks_map: Dict[int, set] = {p['id']: set() for p in pages}

        for lk in links:
            sp_id = lk.get('source_page_id')
            t_url = lk.get('target_url')
            is_int = lk.get('is_internal', True)

            if t_url and t_url in inlinks_map and sp_id is not None:
                inlinks_map[t_url].add(sp_id)

            if sp_id in internal_outlinks_map:
                if is_int:
                    if t_url:
                        internal_outlinks_map[sp_id].add(t_url)
                else:
                    if t_url:
                        external_outlinks_map[sp_id].add(t_url)

        for page in pages:
            pid = page['id']
            u = page['url']
            u_in = len(inlinks_map.get(u, set()))
            u_out = len(internal_outlinks_map.get(pid, set()))
            u_ext = len(external_outlinks_map.get(pid, set()))
            pr = page.get('internal_pagerank', 0.0) or 0.0
            link_score = round(min(100.0, pr * 100.0), 2) if pr > 0 else round(min(100.0, (u_in / max(1, len(pages))) * 100.0), 2)
            await self.db.update_page_columns(
                pid,
                unique_inlinks=u_in,
                unique_outlinks=u_out,
                unique_external_outlinks=u_ext,
                link_score=link_score
            )

        if self.status_updates:
            await self.db.update_links_status_batch(self.status_updates)
            self.status_updates = []

        if total_broken_internal > 0:
            await self._add_issue(
                page_id=None, url=None, severity='critical', issue_type='total_broken_internal_links',
                message=f"Site has {total_broken_internal} broken internal links.",
                recommendation="Review the Internal Links tab and fix all broken internal hyperlinks."
            )

        # External Outbound Link Validation (External Tab)
        external_links = [l for l in links if not l.get('is_internal', True) and l.get('target_url')]
        ext_targets = list(dict.fromkeys(
            l['target_url'] for l in external_links
            if l['target_url'].startswith(('http://', 'https://'))
        ))[:250]

        if ext_targets:
            logger.info(f"Probing {len(ext_targets)} external link targets...")
            ext_status_map: Dict[str, int] = {}
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True, limits=httpx.Limits(max_connections=20)) as ext_client:
                ext_sem = asyncio.Semaphore(15)
                async def _probe_ext(target):
                    async with ext_sem:
                        try:
                            resp = await ext_client.head(target)
                            return target, resp.status_code
                        except Exception:
                            try:
                                resp = await ext_client.get(target)
                                return target, resp.status_code
                            except Exception:
                                return target, 0

                ext_results = await asyncio.gather(*[_probe_ext(t) for t in ext_targets], return_exceptions=True)
                for res in ext_results:
                    if isinstance(res, tuple):
                        t, sc = res
                        ext_status_map[t] = sc

            broken_ext_count = 0
            for el in external_links:
                t = el.get('target_url')
                sc = ext_status_map.get(t)
                if sc is not None:
                    is_broken = sc >= 400 or sc == 0
                    if is_broken:
                        broken_ext_count += 1
                        sp_id = el.get('source_page_id')
                        s_url = el.get('source_url')
                        status_str = f"HTTP {sc}" if sc > 0 else "Connection Timeout / Unreachable"
                        await self._add_issue(
                            page_id=sp_id, url=s_url, severity='critical', issue_type='broken_external_link',
                            message=f"Broken external link ({status_str}): {t}",
                            recommendation="Fix or remove this broken outbound hyperlink to maintain site quality.",
                            element=t
                        )

            if broken_ext_count > 0:
                await self._add_issue(
                    page_id=None, url=None, severity='warning', issue_type='total_broken_external_links',
                    message=f"Site has {broken_ext_count} broken external outbound links.",
                    recommendation="Audit external hyperlinks and replace or remove dead outbound URLs."
                )

        if self.issues_buffer:
            await self.db.add_issues_batch(self.issues_buffer)
            self.issues_buffer = []

        logger.info(f"LinkAnalyzer finished for audit {self.audit_id} (found {total_broken_internal} broken internal links)")

    async def _add_issue(
        self,
        page_id: int | None,
        url: str | None,
        severity: str,
        issue_type: str,
        message: str,
        recommendation: str,
        element: str | None = None
    ):
        self.issues_buffer.append({
            'audit_id': self.audit_id,
            'page_id': page_id,
            'url': url,
            'category': 'links',
            'severity': severity,
            'issue_type': issue_type,
            'message': message,
            'recommendation': recommendation,
            'element': element
        })
        if len(self.issues_buffer) >= 500:
            await self.db.add_issues_batch(self.issues_buffer)
            self.issues_buffer = []
