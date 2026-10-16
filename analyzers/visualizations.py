import logging
from urllib.parse import urlparse
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class VisualizationGenerator:
    """Generates graph and tree topologies for interactive site architecture visualizations."""

    @staticmethod
    async def get_crawl_graph(db, audit_id: str, max_nodes: int = 500) -> Dict[str, Any]:
        """Generates node-link data structure for Force-Directed Crawl Tree visualization."""
        pages = await db.get_pages(audit_id)
        if not pages:
            return {"nodes": [], "links": []}

        audit = await db.get_audit(audit_id)
        seed_url = (audit.get("url") or "").rstrip("/") if audit else ""

        # Find seed page or fallback to first page
        seed_page = None
        other_pages = []
        for p in pages:
            u_clean = (p.get("url") or "").rstrip("/")
            if not seed_page and (u_clean == seed_url or p.get("click_depth") == 0):
                seed_page = p
            else:
                other_pages.append(p)

        if not seed_page and other_pages:
            seed_page = other_pages.pop(0)

        # Sort remaining pages by importance: inlinks desc, click_depth asc
        other_pages.sort(
            key=lambda p: (-(p.get("unique_inlinks") or p.get("inlinks_count") or 0), p.get("click_depth") or p.get("crawl_depth") or 999)
        )

        selected_pages = ([seed_page] if seed_page else []) + other_pages[:max_nodes - 1]
        selected_urls = {p["url"] for p in selected_pages}

        # Build inlink graph to assign parents for hierarchical tree views
        all_links = await db.get_links(audit_id)
        parent_map = {}
        for l in all_links:
            src = l.get("source_url")
            tgt = l.get("target_url")
            if src in selected_urls and tgt in selected_urls and src != tgt:
                if tgt not in parent_map and tgt != seed_url:
                    parent_map[tgt] = src

        nodes = []
        for p in selected_pages:
            u = p["url"]
            parsed = urlparse(u)
            label = parsed.path if parsed.path and parsed.path != "/" else parsed.netloc
            if len(label) > 36:
                label = label[:18] + "..." + label[-15:]

            depth = p.get("click_depth") if p.get("click_depth") is not None else p.get("crawl_depth", 0)
            is_seed = (u.rstrip("/") == seed_url) or (seed_page and u == seed_page.get("url")) or depth == 0

            nodes.append({
                "id": u,
                "label": "/" if (is_seed and not parsed.path.strip("/")) else label,
                "url": u,
                "title": p.get("title") or label,
                "status_code": p.get("status_code", 200),
                "indexability": p.get("indexability") or ("Indexable" if p.get("status_code") == 200 else "Non-Indexable"),
                "depth": depth,
                "inlinks": p.get("unique_inlinks") or p.get("inlinks_count") or 0,
                "outlinks": p.get("unique_outlinks") or p.get("outlinks_count") or 0,
                "pagerank": float(p.get("internal_pagerank") or 0.0),
                "is_orphan": bool(p.get("is_orphan", False)),
                "is_seed": bool(is_seed),
                "parent": parent_map.get(u) if not is_seed else None,
                "word_count": p.get("word_count", 0),
                "content_type": p.get("content_type", "")
            })

        links = []
        seen_edges = set()
        for l in all_links:
            src = l.get("source_url")
            tgt = l.get("target_url")
            if src in selected_urls and tgt in selected_urls and src != tgt:
                edge_key = (src, tgt)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    links.append({
                        "source": src,
                        "target": tgt
                    })
            if len(links) >= 2000:
                break

        return {"nodes": nodes, "links": links}

    @staticmethod
    async def get_directory_tree(db, audit_id: str) -> Dict[str, Any]:
        """Generates a hierarchical directory tree based on URL paths."""
        pages = await db.get_pages(audit_id)
        if not pages:
            return {"name": "Root", "path": "/", "children": []}

        audit = await db.get_audit(audit_id)
        domain = audit.get("domain") if audit else "Website"

        root = {
            "name": domain or "Root",
            "path": "/",
            "url_count": 0,
            "status_200": 0,
            "status_3xx": 0,
            "status_4xx": 0,
            "children": {}
        }

        for p in pages:
            u = p["url"]
            sc = p.get("status_code", 200)
            parsed = urlparse(u)
            segments = [seg for seg in parsed.path.strip("/").split("/") if seg]

            curr = root
            curr["url_count"] += 1
            if sc == 200: curr["status_200"] += 1
            elif 300 <= sc < 400: curr["status_3xx"] += 1
            elif sc >= 400: curr["status_4xx"] += 1

            path_acc = ""
            for seg in segments[:5]:
                path_acc += f"/{seg}"
                if seg not in curr["children"]:
                    curr["children"][seg] = {
                        "name": seg,
                        "path": path_acc,
                        "url_count": 0,
                        "status_200": 0,
                        "status_3xx": 0,
                        "status_4xx": 0,
                        "children": {}
                    }
                curr = curr["children"][seg]
                curr["url_count"] += 1
                if sc == 200: curr["status_200"] += 1
                elif 300 <= sc < 400: curr["status_3xx"] += 1
                elif sc >= 400: curr["status_4xx"] += 1

        def format_node(node: Dict[str, Any]) -> Dict[str, Any]:
            children_dict = node.pop("children", {})
            children_list = [format_node(c) for c in children_dict.values()]
            # Sort children by url_count descending
            children_list.sort(key=lambda c: -c["url_count"])
            node["children"] = children_list
            return node

        return format_node(root)

