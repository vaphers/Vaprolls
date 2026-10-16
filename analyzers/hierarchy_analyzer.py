import logging
from collections import deque
from urllib.parse import urlparse
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)

class HierarchyAnalyzer:
    """Computes exact Click Depth via Breadth-First Search (BFS) and identifies Orphan Pages."""

    def __init__(self, database, audit_id: str):
        self.db = database
        self.audit_id = audit_id

    async def analyze(self):
        try:
            audit = await self.db.get_audit(self.audit_id)
            if not audit:
                return

            seed_url = audit.get("url") or ""
            pages = await self.db.get_pages(self.audit_id)
            if not pages:
                return

            url_to_page = {p["url"]: p for p in pages}
            all_links = await self.db.get_links(self.audit_id)

            # 1. Build Internal Link Graph
            adj_list: Dict[str, Set[str]] = {}
            inlinks_count: Dict[str, int] = {p["url"]: 0 for p in pages}

            for link in all_links:
                src = link.get("source_url")
                tgt = link.get("target_url")
                is_int = link.get("is_internal")

                if src and tgt and is_int and src in url_to_page and tgt in url_to_page:
                    if src not in adj_list:
                        adj_list[src] = set()
                    adj_list[src].add(tgt)
                    inlinks_count[tgt] = inlinks_count.get(tgt, 0) + 1

            # Determine start seed URL
            start_node = seed_url
            if start_node not in url_to_page:
                # Find homepage or page with depth 0
                for p in pages:
                    u = p["url"]
                    parsed = urlparse(u)
                    if parsed.path in ("", "/"):
                        start_node = u
                        break
                if start_node not in url_to_page and pages:
                    start_node = pages[0]["url"]

            # 2. BFS for Exact Click Depth
            click_depths: Dict[str, int] = {}
            queue = deque([start_node])
            click_depths[start_node] = 0

            while queue:
                curr = queue.popleft()
                curr_depth = click_depths[curr]

                for nxt in adj_list.get(curr, []):
                    if nxt not in click_depths:
                        click_depths[nxt] = curr_depth + 1
                        queue.append(nxt)

            # 3. Detect Orphan Pages and Update Database
            orphan_count = 0
            for url, page in url_to_page.items():
                page_id = page["id"]
                inlinks = inlinks_count.get(url, 0)
                exact_depth = click_depths.get(url, -1)

                is_orphan = 1 if (inlinks == 0 and url != start_node) else 0

                # If unreachable from seed through navigation, set click depth to -1 or large
                final_depth = exact_depth if exact_depth != -1 else (page.get("crawl_depth") or 99)

                await self.db.update_page_columns(
                    page_id,
                    click_depth=final_depth,
                    is_orphan=is_orphan,
                    unique_inlinks=inlinks
                )

                if is_orphan:
                    orphan_count += 1
                    await self.db.add_issue(
                        self.audit_id,
                        page_id=page_id,
                        issue_type="orphan_page",
                        category="Links",
                        severity="high",
                        title="Orphan Page (Zero Internal Inlinks)",
                        description=f"The URL '{url}' has 0 internal inlinks pointing to it from the website crawl. It is isolated from the navigation structure.",
                        recommendation="Link to this page from relevant parent categories, or remove it from sitemaps/redirect if obsolete."
                    )

            logger.info(f"[HierarchyAnalyzer] Exact click depth computed for {len(pages)} pages. Detected {orphan_count} orphan pages.")

        except Exception as e:
            logger.error(f"HierarchyAnalyzer error for {self.audit_id}: {e}", exc_info=True)

