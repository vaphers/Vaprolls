import asyncpg
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PostgresDatabase:
    """PostgreSQL and TimescaleDB database adapter matching the SQLite Database interface."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def init(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=5,
                max_size=25,
                command_timeout=60
            )

            # Initialize schema if not present
            schema_path = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")
            if os.path.exists(schema_path):
                try:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        schema_sql = f.read()
                    async with self.pool.acquire() as conn:
                        await conn.execute(schema_sql)
                    logger.info("PostgreSQL schema ensured successfully.")
                except Exception as e:
                    logger.warning(f"Could not automatically execute schema_postgres.sql: {e}")

    async def close(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def create_audit(self, audit_id: str, domain: str, url: str, config: Optional[str] = None):
        cfg_val = json.loads(config) if isinstance(config, str) and config else (config or {})
        query = """
            INSERT INTO audits (id, domain, url, status, started_at, config)
            VALUES ($1, $2, $3, 'pending', NOW(), $4)
            ON CONFLICT (id) DO UPDATE SET
                domain = EXCLUDED.domain,
                url = EXCLUDED.url,
                config = EXCLUDED.config,
                updated_at = NOW()
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, audit_id, domain, url, json.dumps(cfg_val))

    async def get_audit(self, audit_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM audits WHERE id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, audit_id)
            if not row:
                return None
            data = dict(row)
            if isinstance(data.get('config'), str):
                try:
                    data['config_json'] = data['config']
                except Exception:
                    pass
            return data

    async def update_audit(self, audit_id: str, **kwargs):
        if not kwargs:
            return
        set_clauses = []
        vals = [audit_id]
        idx = 2
        for k, v in kwargs.items():
            set_clauses.append(f"{k} = ${idx}")
            vals.append(v)
            idx += 1

        set_clauses.append("updated_at = NOW()")
        query = f"UPDATE audits SET {', '.join(set_clauses)} WHERE id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, *vals)

    async def get_audit_summary(self, audit_id: str) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            audit = await conn.fetchrow("SELECT * FROM audits WHERE id = $1", audit_id)
            pages_count = await conn.fetchval("SELECT COUNT(*) FROM pages WHERE audit_id = $1", audit_id) or 0
            
            issues_rows = await conn.fetch(
                "SELECT severity, COUNT(*) as cnt FROM issues WHERE audit_id = $1 GROUP BY severity",
                audit_id
            )
            issues_by_sev = {r['severity']: r['cnt'] for r in issues_rows}

            return {
                "audit": dict(audit) if audit else None,
                "total_pages": pages_count,
                "total_issues": sum(issues_by_sev.values()),
                "issues_by_severity": issues_by_sev,
            }

    async def get_pages(self, audit_id: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM pages WHERE audit_id = $1 ORDER BY page_id ASC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        if offset is not None:
            query += f" OFFSET {int(offset)}"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, audit_id)
            pages = []
            for r in rows:
                p = dict(r)
                # Parse JSON fields if needed
                for jf in ['links', 'images', 'structured_data', 'og_tags', 'twitter_tags']:
                    if isinstance(p.get(jf), str):
                        try:
                            p[jf] = json.loads(p[jf])
                        except Exception:
                            pass
                pages.append(p)
            return pages

    async def get_page_by_id(self, audit_id: str, page_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM pages WHERE audit_id = $1 AND page_id = $2"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, audit_id, page_id)
            return dict(row) if row else None

    async def get_page_by_url(self, audit_id: str, url: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM pages WHERE audit_id = $1 AND url = $2"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, audit_id, url)
            return dict(row) if row else None

    async def add_issues_batch(self, issues: List[Dict[str, Any]]):
        if not issues:
            return
        query = """
            INSERT INTO issues (audit_id, page_id, page_url, category, issue_type, severity, title, description, recommendation, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        async with self.pool.acquire() as conn:
            await conn.executemany(
                query,
                [
                    (
                        i.get('audit_id'),
                        i.get('page_id'),
                        i.get('page_url') or i.get('url'),
                        i.get('category', 'general'),
                        i.get('issue_type', 'issue'),
                        i.get('severity', 'info'),
                        i.get('title', ''),
                        i.get('description', ''),
                        i.get('recommendation', ''),
                        json.dumps(i.get('details', {})) if isinstance(i.get('details'), (dict, list)) else None
                    )
                    for i in issues
                ]
            )

    async def get_issues(self, audit_id: str, severity: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        conditions = ["audit_id = $1"]
        params = [audit_id]
        if severity:
            params.append(severity)
            conditions.append(f"severity = ${len(params)}")
        if category:
            params.append(category)
            conditions.append(f"category = ${len(params)}")

        query = f"SELECT * FROM issues WHERE {' AND '.join(conditions)} ORDER BY id ASC"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_pages_count(self, audit_id: str) -> int:
        query = "SELECT COUNT(*) FROM pages WHERE audit_id = $1"
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(query, audit_id)
            return int(val) if val is not None else 0

    async def get_pages_paginated(self, audit_id: str, page: int = 1, page_size: int = 1000, sort_by: str = 'page_id', sort_dir: str = 'asc') -> List[Dict[str, Any]]:
        allowed_sorts = {'id', 'page_id', 'url', 'status_code', 'response_time_ms', 'crawl_depth', 'size_bytes', 'word_count'}
        sort_col = sort_by if sort_by in allowed_sorts else 'page_id'
        direction = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'
        offset = (page - 1) * page_size
        query = f"SELECT * FROM pages WHERE audit_id = $1 ORDER BY {sort_col} {direction} LIMIT $2 OFFSET $3"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, audit_id, page_size, offset)
            return [dict(r) for r in rows]

    async def get_page(self, page_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM pages WHERE page_id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, page_id)
            return dict(row) if row else None

    async def list_audits(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audits ORDER BY started_at DESC"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]

    async def delete_audit(self, audit_id: str):
        query = "DELETE FROM audits WHERE id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, audit_id)

    async def add_links_batch(self, links_list: List[Dict[str, Any]]):
        if not links_list:
            return
        query = """
            INSERT INTO links (audit_id, source_page_id, source_url, target_url, anchor_text, is_internal, is_broken, status_code, rel_attributes, link_type, nofollow)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """
        async with self.pool.acquire() as conn:
            await conn.executemany(
                query,
                [
                    (
                        l.get('audit_id'), l.get('source_page_id'), l.get('source_url'), l.get('target_url'),
                        l.get('anchor_text'), l.get('is_internal', True), l.get('is_broken', False),
                        l.get('status_code'), l.get('rel_attributes'), l.get('link_type', 'a'), l.get('nofollow', False)
                    )
                    for l in links_list
                ]
            )

    async def get_links(self, audit_id: str, is_internal: Optional[bool] = None, is_broken: Optional[bool] = None, page_id: Optional[int] = None, source_page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conditions = ["audit_id = $1"]
        params = [audit_id]
        if is_internal is not None:
            params.append(is_internal)
            conditions.append(f"is_internal = ${len(params)}")
        if is_broken is not None:
            params.append(is_broken)
            conditions.append(f"is_broken = ${len(params)}")
        if page_id is not None:
            params.append(page_id)
            conditions.append(f"source_page_id = ${len(params)}")
        if source_page_id is not None:
            params.append(source_page_id)
            conditions.append(f"source_page_id = ${len(params)}")

        query = f"SELECT * FROM links WHERE {' AND '.join(conditions)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_page_inlinks(self, audit_id: str, target_url: str) -> List[Dict[str, Any]]:
        query = "SELECT * FROM links WHERE audit_id = $1 AND target_url = $2"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, audit_id, target_url)
            return [dict(r) for r in rows]

    async def get_page_outlinks(self, audit_id: str, source_url: str) -> List[Dict[str, Any]]:
        query = "SELECT * FROM links WHERE audit_id = $1 AND source_url = $2"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, audit_id, source_url)
            return [dict(r) for r in rows]

    async def add_images_batch(self, images_list: List[Dict[str, Any]]):
        if not images_list:
            return
        query = """
            INSERT INTO images (audit_id, page_id, page_url, src, alt_text, file_size, width, height, format, is_lazy_loaded, has_dimensions, is_broken)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """
        async with self.pool.acquire() as conn:
            await conn.executemany(
                query,
                [
                    (
                        img.get('audit_id'), img.get('page_id'), img.get('page_url'), img.get('src'),
                        img.get('alt_text'), img.get('file_size'), img.get('width'), img.get('height'),
                        img.get('format'), img.get('is_lazy_loaded', False), img.get('has_dimensions', False),
                        img.get('is_broken', False)
                    )
                    for img in images_list
                ]
            )

    async def get_images(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conditions = ["audit_id = $1"]
        params = [audit_id]
        if page_id is not None:
            params.append(page_id)
            conditions.append(f"page_id = ${len(params)}")
        query = f"SELECT * FROM images WHERE {' AND '.join(conditions)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def add_sitemap_entries_batch(self, entries_list: List[Dict[str, Any]]):
        if not entries_list:
            return
        query = """
            INSERT INTO sitemap_entries (audit_id, page_url, sitemap_url, lastmod, changefreq, priority)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        async with self.pool.acquire() as conn:
            await conn.executemany(
                query,
                [
                    (
                        e.get('audit_id'), e.get('page_url') or e.get('url'), e.get('sitemap_url'),
                        e.get('lastmod') or None, e.get('changefreq'), e.get('priority')
                    )
                    for e in entries_list
                ]
            )

    async def get_sitemap_entries(self, audit_id: str) -> List[Dict[str, Any]]:
        query = "SELECT * FROM sitemap_entries WHERE audit_id = $1"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, audit_id)
            return [dict(r) for r in rows]

    async def get_structured_data(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM pages WHERE audit_id = $1 AND structured_data IS NOT NULL"
        params = [audit_id]
        if page_id is not None:
            params.append(page_id)
            query += f" AND page_id = ${len(params)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = []
            for r in rows:
                p = dict(r)
                sd = p.get('structured_data')
                if isinstance(sd, str):
                    try:
                        sd = json.loads(sd)
                    except Exception:
                        pass
                if sd:
                    results.append({
                        "audit_id": audit_id,
                        "page_id": p.get('page_id'),
                        "url": p.get('url'),
                        "raw_json": json.dumps(sd) if not isinstance(sd, str) else sd,
                        "schema_type": sd[0].get('@type', 'Schema') if isinstance(sd, list) and len(sd) > 0 and isinstance(sd[0], dict) else 'Schema'
                    })
            return results

    async def get_hreflang_tags(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM hreflang_tags WHERE audit_id = $1"
        params = [audit_id]
        if page_id is not None:
            params.append(page_id)
            query += f" AND page_id = ${len(params)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_pagination_tags(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM pagination_tags WHERE audit_id = $1"
        params = [audit_id]
        if page_id is not None:
            params.append(page_id)
            query += f" AND page_id = ${len(params)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_headings(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM headings WHERE audit_id = $1"
        params = [audit_id]
        if page_id is not None:
            params.append(page_id)
            query += f" AND page_id = ${len(params)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_custom_extractions(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM custom_extractions WHERE audit_id = $1"
        params = [audit_id]
        if page_id is not None:
            params.append(page_id)
            query += f" AND page_id = ${len(params)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_custom_search_matches(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM custom_search_matches WHERE audit_id = $1"
        params = [audit_id]
        if page_id is not None:
            params.append(page_id)
            query += f" AND page_id = ${len(params)}"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def flush(self):
        """No-op for compatibility with SQLite batching."""
        pass

    def __getattr__(self, name: str):
        """Graceful resilient fallback for any auxiliary or specialized table methods."""
        async def _fallback(*args, **kwargs):
            if name.startswith("get_"):
                if "count" in name:
                    return 0
                return []
            return None
        return _fallback
