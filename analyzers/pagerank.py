import logging
from typing import Dict, Any, List, Set
from database.db import Database

logger = logging.getLogger(__name__)

class PageRankAnalyzer:
    """
    Computes mathematical Internal PageRank (Link Equity) across the site's internal link graph.
    Uses standard power iteration with damping factor d = 0.85.
    Scores are normalized from 0.0 to 100.0 and saved to each page record.
    """
    def __init__(self, db: Database, audit_id: str, damping: float = 0.85, max_iter: int = 100, tol: float = 1e-6):
        self.db = db
        self.audit_id = audit_id
        self.damping = damping
        self.max_iter = max_iter
        self.tol = tol

    async def analyze(self):
        logger.info(f"Starting Internal PageRank calculation for audit {self.audit_id}")
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        url_to_page = {p['url']: p for p in pages}
        nodes = list(url_to_page.keys())
        N = len(nodes)
        if N == 0:
            return

        node_index = {url: i for i, url in enumerate(nodes)}

        # Fetch internal links
        all_links = await self.db.get_links(self.audit_id, is_internal=True)

        # Build adjacency graph
        out_links: Dict[int, Set[int]] = {i: set() for i in range(N)}
        in_links: Dict[int, Set[int]] = {i: set() for i in range(N)}

        for link in all_links:
            source = link.get('source_url')
            target = link.get('target_url')
            if source in node_index and target in node_index:
                s_idx = node_index[source]
                t_idx = node_index[target]
                if s_idx != t_idx:  # Skip self-links
                    out_links[s_idx].add(t_idx)
                    in_links[t_idx].add(s_idx)

        # Initialize PageRank vector uniformly
        pr = [1.0 / N] * N

        # Power iteration
        for iteration in range(self.max_iter):
            next_pr = [0.0] * N
            dangling_sum = sum(pr[i] for i in range(N) if len(out_links[i]) == 0)

            for i in range(N):
                incoming_sum = sum(pr[j] / len(out_links[j]) for j in in_links[i])
                next_pr[i] = ((1.0 - self.damping) / N) + self.damping * (incoming_sum + (dangling_sum / N))

            # Check convergence
            diff = sum(abs(next_pr[i] - pr[i]) for i in range(N))
            pr = next_pr
            if diff < self.tol:
                break

        # Normalize PageRank to 0.0 - 100.0 scale
        max_pr = max(pr) if pr else 1.0
        min_pr = min(pr) if pr else 0.0
        pr_range = max_pr - min_pr if max_pr > min_pr else 1.0

        for i, url in enumerate(nodes):
            normalized_score = round(((pr[i] - min_pr) / pr_range) * 100.0, 2)
            page = url_to_page[url]
            page_id = page['id']
            await self.db.update_page_pagerank(self.audit_id, page_id, normalized_score)

            # Issue Diagnostic 1: Equity Trap
            lower_url = url.lower()
            utility_terms = ['privacy', 'terms', 'cookie', 'legal', 'login', 'disclaimer']
            if any(term in lower_url for term in utility_terms) and normalized_score > 60.0:
                await self.db.add_issue(
                    audit_id=self.audit_id,
                    page_id=page_id,
                    url=url,
                    category='links',
                    severity='warning',
                    issue_type='equity_trap',
                    message=f"Utility page hoards high internal PageRank ({normalized_score}/100)",
                    recommendation="Remove sitewide/footer links to low-priority utility pages or consolidate links so equity flows to conversion pages.",
                    element=url
                )

            # Issue Diagnostic 2: Low-Authority Target Page
            depth = page.get('crawl_depth', 0)
            if depth == 1 and normalized_score < 15.0 and len(in_links[i]) < 3:
                await self.db.add_issue(
                    audit_id=self.audit_id,
                    page_id=page_id,
                    url=url,
                    category='links',
                    severity='info',
                    issue_type='low_internal_authority',
                    message=f"Top-level page receives very low internal PageRank ({normalized_score}/100)",
                    recommendation="Add contextual in-content links from high-authority pages to boost this URL's internal link equity.",
                    element=url
                )

        logger.info(f"Completed PageRank calculation for {N} pages in audit {self.audit_id}")
