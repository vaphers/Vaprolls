import logging
from typing import Dict, Any, List, Optional
from database.db import Database

logger = logging.getLogger(__name__)

class AuditComparator:
    """
    Compares two audits (e.g. Pre-Migration vs Post-Migration or Staging vs Production)
    and computes complete diffs for status codes, metadata, canonicals, indexability,
    internal PageRank, and added/removed URLs.
    """
    def __init__(self, db: Database, baseline_audit_id: str, current_audit_id: str):
        self.db = db
        self.baseline_id = baseline_audit_id
        self.current_id = current_audit_id

    async def compare(self) -> Dict[str, Any]:
        baseline_audit = await self.db.get_audit(self.baseline_id)
        current_audit = await self.db.get_audit(self.current_id)

        if not baseline_audit or not current_audit:
            raise ValueError("One or both audit IDs not found.")

        pages_1 = await self.db.get_pages(self.baseline_id)
        pages_2 = await self.db.get_pages(self.current_id)

        map_1 = {p['url']: p for p in pages_1}
        map_2 = {p['url']: p for p in pages_2}

        urls_1 = set(map_1.keys())
        urls_2 = set(map_2.keys())

        added_urls = list(urls_2 - urls_1)
        removed_urls = list(urls_1 - urls_2)
        common_urls = urls_1 & urls_2

        status_changes = []
        title_changes = []
        desc_changes = []
        h1_changes = []
        canonical_changes = []
        indexability_changes = []
        pagerank_changes = []

        for url in common_urls:
            p1 = map_1[url]
            p2 = map_2[url]

            # Status code diff
            if p1.get('status_code') != p2.get('status_code'):
                status_changes.append({
                    'url': url,
                    'old': p1.get('status_code'),
                    'new': p2.get('status_code')
                })

            # Title diff
            if (p1.get('title') or '').strip() != (p2.get('title') or '').strip():
                title_changes.append({
                    'url': url,
                    'old': p1.get('title'),
                    'new': p2.get('title')
                })

            # Meta Description diff
            if (p1.get('meta_description') or '').strip() != (p2.get('meta_description') or '').strip():
                desc_changes.append({
                    'url': url,
                    'old': p1.get('meta_description'),
                    'new': p2.get('meta_description')
                })

            # H1 diff
            if (p1.get('h1') or '').strip() != (p2.get('h1') or '').strip():
                h1_changes.append({
                    'url': url,
                    'old': p1.get('h1'),
                    'new': p2.get('h1')
                })

            # Canonical diff
            if (p1.get('canonical_url') or '').strip() != (p2.get('canonical_url') or '').strip():
                canonical_changes.append({
                    'url': url,
                    'old': p1.get('canonical_url'),
                    'new': p2.get('canonical_url')
                })

            # Indexability diff
            if p1.get('is_indexable') != p2.get('is_indexable'):
                indexability_changes.append({
                    'url': url,
                    'old': p1.get('is_indexable'),
                    'new': p2.get('is_indexable')
                })

            # PageRank shift (changes > 5.0 points)
            pr1 = p1.get('internal_pagerank', 0.0) or 0.0
            pr2 = p2.get('internal_pagerank', 0.0) or 0.0
            if abs(pr2 - pr1) >= 5.0:
                pagerank_changes.append({
                    'url': url,
                    'old': pr1,
                    'new': pr2,
                    'diff': round(pr2 - pr1, 2)
                })

        summary_1 = await self.db.get_audit_summary(self.baseline_id)
        summary_2 = await self.db.get_audit_summary(self.current_id)

        return {
            'baseline_audit': baseline_audit,
            'current_audit': current_audit,
            'summary': {
                'baseline_pages': len(pages_1),
                'current_pages': len(pages_2),
                'pages_diff': len(pages_2) - len(pages_1),
                'added_count': len(added_urls),
                'removed_count': len(removed_urls),
                'status_changes_count': len(status_changes),
                'title_changes_count': len(title_changes),
                'canonical_changes_count': len(canonical_changes),
                'indexability_changes_count': len(indexability_changes),
                'baseline_health_score': baseline_audit.get('health_score', 0),
                'current_health_score': current_audit.get('health_score', 0),
                'health_score_diff': round((current_audit.get('health_score', 0) or 0) - (baseline_audit.get('health_score', 0) or 0), 1)
            },
            'added_urls': added_urls[:100],
            'removed_urls': removed_urls[:100],
            'status_changes': status_changes,
            'title_changes': title_changes[:100],
            'desc_changes': desc_changes[:100],
            'h1_changes': h1_changes[:100],
            'canonical_changes': canonical_changes[:100],
            'indexability_changes': indexability_changes,
            'pagerank_changes': sorted(pagerank_changes, key=lambda x: abs(x['diff']), reverse=True)[:50]
        }
