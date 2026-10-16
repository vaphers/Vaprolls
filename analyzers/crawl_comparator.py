import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class CrawlComparator:
    """Compares two audits (e.g., Staging vs Prod, or Before Migration vs After Migration)."""

    @staticmethod
    async def compare(db, base_id: str, compare_id: str) -> Dict[str, Any]:
        """Compares base audit (A) with comparison audit (B)."""
        base_audit = await db.get_audit(base_id)
        compare_audit = await db.get_audit(compare_id)

        if not base_audit or not compare_audit:
            return {"error": "One or both audits not found"}

        base_pages = await db.get_pages(base_id)
        comp_pages = await db.get_pages(compare_id)

        base_map = {p["url"]: p for p in base_pages}
        comp_map = {p["url"]: p for p in comp_pages}

        base_urls = set(base_map.keys())
        comp_urls = set(comp_map.keys())

        # 1. URL additions & removals
        added_urls = comp_urls - base_urls
        removed_urls = base_urls - comp_urls
        common_urls = base_urls & comp_urls

        # 2. Detailed differences for common URLs
        status_changed = []
        title_changed = []
        meta_desc_changed = []
        canonical_changed = []
        indexability_changed = []

        for u in common_urls:
            p_base = base_map[u]
            p_comp = comp_map[u]

            # Status Code
            b_sc = p_base.get("status_code", 0)
            c_sc = p_comp.get("status_code", 0)
            if b_sc != c_sc:
                status_changed.append({
                    "url": u,
                    "base_value": b_sc,
                    "comp_value": c_sc,
                    "change": f"{b_sc} -> {c_sc}"
                })

            # Title
            b_title = p_base.get("title") or ""
            c_title = p_comp.get("title") or ""
            if b_title != c_title:
                title_changed.append({
                    "url": u,
                    "base_value": b_title,
                    "comp_value": c_title
                })

            # Meta Description
            b_desc = p_base.get("meta_description") or ""
            c_desc = p_comp.get("meta_description") or ""
            if b_desc != c_desc:
                meta_desc_changed.append({
                    "url": u,
                    "base_value": b_desc,
                    "comp_value": c_desc
                })

            # Canonical
            b_canon = p_base.get("canonical_url") or ""
            c_canon = p_comp.get("canonical_url") or ""
            if b_canon != c_canon:
                canonical_changed.append({
                    "url": u,
                    "base_value": b_canon,
                    "comp_value": c_canon
                })

            # Indexability
            b_idx = bool(p_base.get("is_indexable"))
            c_idx = bool(p_comp.get("is_indexable"))
            if b_idx != c_idx:
                indexability_changed.append({
                    "url": u,
                    "base_value": "Indexable" if b_idx else "Non-Indexable",
                    "comp_value": "Indexable" if c_idx else "Non-Indexable"
                })

        # Format added rows
        added_rows = [
            {
                "url": u,
                "status_code": comp_map[u].get("status_code", 0),
                "title": comp_map[u].get("title", ""),
                "content_type": comp_map[u].get("content_type", "")
            }
            for u in added_urls
        ]

        # Format removed rows
        removed_rows = [
            {
                "url": u,
                "status_code": base_map[u].get("status_code", 0),
                "title": base_map[u].get("title", ""),
                "content_type": base_map[u].get("content_type", "")
            }
            for u in removed_urls
        ]

        return {
            "base_audit": {
                "id": base_id,
                "url": base_audit.get("url"),
                "total_pages": len(base_pages),
                "health_score": base_audit.get("health_score", 0),
                "total_issues": base_audit.get("total_issues", 0),
                "completed_at": base_audit.get("completed_at")
            },
            "comp_audit": {
                "id": compare_id,
                "url": compare_audit.get("url"),
                "total_pages": len(comp_pages),
                "health_score": compare_audit.get("health_score", 0),
                "total_issues": compare_audit.get("total_issues", 0),
                "completed_at": compare_audit.get("completed_at")
            },
            "summary": {
                "total_common": len(common_urls),
                "added_count": len(added_urls),
                "removed_count": len(removed_urls),
                "status_changed_count": len(status_changed),
                "title_changed_count": len(title_changed),
                "meta_desc_changed_count": len(meta_desc_changed),
                "canonical_changed_count": len(canonical_changed),
                "indexability_changed_count": len(indexability_changed),
            },
            "added_urls": added_rows[:500],
            "removed_urls": removed_rows[:500],
            "status_changed": status_changed[:500],
            "title_changed": title_changed[:500],
            "meta_desc_changed": meta_desc_changed[:500],
            "canonical_changed": canonical_changed[:500],
            "indexability_changed": indexability_changed[:500],
        }

