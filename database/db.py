import aiosqlite
import logging
from typing import Dict, Any, List, Optional
from .models import SCHEMA_SQL

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def init(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode = WAL;")
        await self.conn.execute("PRAGMA synchronous = NORMAL;")
        await self.conn.execute("PRAGMA cache_size = -64000;")
        await self.conn.execute("PRAGMA temp_store = MEMORY;")
        await self.conn.executescript(SCHEMA_SQL)
        for col, col_type in [
            ("viewport", "TEXT"),
            ("parent_url", "TEXT"),
            ("language", "TEXT"),
            ("robots_meta", "TEXT"),
            ("page_type", "TEXT"),
            ("mime_type", "TEXT")
        ]:
            try:
                await self.conn.execute(f"ALTER TABLE pages ADD COLUMN {col} {col_type};")
            except Exception:
                pass
        await self.conn.commit()

    async def _insert(self, table: str, data: Dict[str, Any]) -> int:
        import json as _json
        keys = list(data.keys())
        values = []
        for v in data.values():
            if isinstance(v, (list, dict)):
                values.append(_json.dumps(v))
            else:
                values.append(v)
        placeholders = ', '.join(['?'] * len(keys))
        cols = ', '.join(keys)
        
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        cursor = await self.conn.execute(query, values)
        await self.conn.commit()
        return cursor.lastrowid

    async def create_audit(self, audit_id: str, domain: str, url: str, config: str) -> str:
        query = "INSERT INTO audits (id, domain, url, status, config_json) VALUES (?, ?, ?, ?, ?)"
        await self.conn.execute(query, (audit_id, domain, url, 'pending', config))
        await self.conn.commit()
        return audit_id

    async def update_audit(self, audit_id: str, **kwargs):
        if not kwargs:
            return
        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(audit_id)
        
        query = f"UPDATE audits SET {set_clause} WHERE id = ?"
        await self.conn.execute(query, values)
        await self.conn.commit()

    async def get_audit(self, audit_id: str) -> Optional[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM audits WHERE id = ?", (audit_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_audits(self) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM audits ORDER BY started_at DESC") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_page(self, audit_id: str, **page_data) -> int:
        page_data['audit_id'] = audit_id
        
        keys = list(page_data.keys())
        values = list(page_data.values())
        placeholders = ', '.join(['?'] * len(keys))
        cols = ', '.join(keys)
        set_clause = ', '.join([f"{k}=EXCLUDED.{k}" for k in keys if k not in ('id', 'audit_id', 'url')])

        query = f"""
            INSERT INTO pages ({cols}) VALUES ({placeholders})
            ON CONFLICT(audit_id, url) DO UPDATE SET {set_clause}
        """
        cursor = await self.conn.execute(query, values)
        await self.conn.commit()
        
        if cursor.lastrowid:
            return cursor.lastrowid
        else:
            # If updated, lastrowid might be 0, so we fetch it
            async with self.conn.execute("SELECT id FROM pages WHERE audit_id = ? AND url = ?", (audit_id, page_data.get('url'))) as c:
                row = await c.fetchone()
                return row['id'] if row else None

    async def get_page(self, page_id: int) -> Optional[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_pages(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM pages WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def get_page_by_url(self, audit_id: str, url: str) -> Optional[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM pages WHERE audit_id = ? AND url = ?", (audit_id, url)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_issue(self, audit_id: str, page_id: Optional[int] = None, **issue_data):
        issue_data['audit_id'] = audit_id
        if page_id is not None:
            issue_data['page_id'] = page_id
        await self._insert('issues', issue_data)

    async def add_issues_batch(self, issues_list: List[Dict[str, Any]]):
        if not issues_list:
            return
        import json as _json
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        query = """
            INSERT INTO issues (audit_id, page_id, url, category, severity, issue_type, message, recommendation, element, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            (
                iss.get('audit_id'),
                iss.get('page_id'),
                iss.get('url'),
                iss.get('category'),
                iss.get('severity'),
                iss.get('issue_type'),
                iss.get('message'),
                iss.get('recommendation'),
                _json.dumps(iss['element']) if isinstance(iss.get('element'), (dict, list)) else (str(iss['element']) if iss.get('element') is not None else None),
                iss.get('created_at', now)
            )
            for iss in issues_list
        ]
        await self.conn.executemany(query, params)
        await self.conn.commit()

    async def get_issues(self, audit_id: str, category: Optional[str] = None, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM issues WHERE audit_id = ?"
        params = [audit_id]
        if category:
            query += " AND category = ?"
            params.append(category)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_link(self, audit_id: str, source_page_id: int, **link_data):
        link_data['audit_id'] = audit_id
        link_data['source_page_id'] = source_page_id
        await self._insert('links', link_data)

    async def add_links_batch(self, links_list: List[Dict[str, Any]]):
        if not links_list:
            return
        query = """
            INSERT INTO links (audit_id, source_page_id, source_url, target_url, anchor_text, is_internal, is_broken, status_code, rel_attributes, link_type, nofollow)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            (
                l.get('audit_id'), l.get('source_page_id'), l.get('source_url'), l.get('target_url'),
                l.get('anchor_text'), l.get('is_internal', True), l.get('is_broken', False),
                l.get('status_code'), l.get('rel_attributes'), l.get('link_type', 'a'), l.get('nofollow', False)
            )
            for l in links_list
        ]
        await self.conn.executemany(query, params)
        await self.conn.commit()

    async def get_links(self, audit_id: str, is_internal: Optional[bool] = None, is_broken: Optional[bool] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM links WHERE audit_id = ?"
        params = [audit_id]
        if is_internal is not None:
            query += " AND is_internal = ?"
            params.append(is_internal)
        if is_broken is not None:
            query += " AND is_broken = ?"
            params.append(is_broken)
            
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def update_link(self, link_id: int, **kwargs):
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [link_id]
        await self.conn.execute(f"UPDATE links SET {set_clause} WHERE id = ?", values)
        await self.conn.commit()

    async def add_image(self, audit_id: str, page_id: int, **image_data):
        image_data['audit_id'] = audit_id
        image_data['page_id'] = page_id
        await self._insert('images', image_data)

    async def add_images_batch(self, images_list: List[Dict[str, Any]]):
        if not images_list:
            return
        query = """
            INSERT INTO images (audit_id, page_id, page_url, src, alt_text, file_size, width, height, format, is_lazy_loaded, has_dimensions, is_broken)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            (
                i.get('audit_id'), i.get('page_id'), i.get('page_url'), i.get('src'),
                i.get('alt_text'), i.get('file_size'), i.get('width'), i.get('height'),
                i.get('format'), i.get('is_lazy_loaded', False), i.get('has_dimensions', False), i.get('is_broken', False)
            )
            for i in images_list
        ]
        await self.conn.executemany(query, params)
        await self.conn.commit()

    async def get_images(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM images WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_keyword(self, audit_id: str, page_id: int, **keyword_data):
        keyword_data['audit_id'] = audit_id
        keyword_data['page_id'] = page_id
        await self._insert('keywords', keyword_data)

    async def get_keywords(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM keywords WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_heading(self, page_id: int, tag: str, text: str, order_index: int):
        await self._insert('headings', {'page_id': page_id, 'tag': tag, 'text': text, 'order_index': order_index})

    async def add_headings_batch(self, headings_list: List[tuple]):
        if not headings_list:
            return
        query = "INSERT INTO headings (page_id, tag, text, order_index) VALUES (?, ?, ?, ?)"
        await self.conn.executemany(query, headings_list)
        await self.conn.commit()

    async def get_headings(self, page_id: int) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM headings WHERE page_id = ? ORDER BY order_index", (page_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_resource(self, audit_id: str, page_id: int, **resource_data):
        resource_data['audit_id'] = audit_id
        resource_data['page_id'] = page_id
        await self._insert('resources', resource_data)

    async def get_resources(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM resources WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_structured_data(self, audit_id: str, page_id: int, **data):
        data['audit_id'] = audit_id
        data['page_id'] = page_id
        await self._insert('structured_data', data)

    async def get_structured_data(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM structured_data WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_performance_metrics(self, audit_id: str, page_id: int, **metrics):
        metrics['audit_id'] = audit_id
        metrics['page_id'] = page_id
        await self._insert('performance_metrics', metrics)

    async def get_performance_metrics(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM performance_metrics WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def get_audit_summary(self, audit_id: str) -> Dict[str, Any]:
        summary = {
            'total_pages': 0,
            'issues_by_severity': {},
            'issues_by_category': {}
        }
        
        async with self.conn.execute("SELECT COUNT(*) as count FROM pages WHERE audit_id = ?", (audit_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                summary['total_pages'] = row['count']
                
        async with self.conn.execute("SELECT severity, COUNT(*) as count FROM issues WHERE audit_id = ? GROUP BY severity", (audit_id,)) as cursor:
            for row in await cursor.fetchall():
                summary['issues_by_severity'][row['severity']] = row['count']
                
        async with self.conn.execute("SELECT category, COUNT(*) as count FROM issues WHERE audit_id = ? GROUP BY category", (audit_id,)) as cursor:
            for row in await cursor.fetchall():
                summary['issues_by_category'][row['category']] = row['count']
                
        return summary

    async def add_custom_extraction(self, audit_id: str, page_id: int, page_url: str, rule_name: str, extracted_value: str):
        await self._insert('custom_extractions', {
            'audit_id': audit_id, 'page_id': page_id, 'page_url': page_url,
            'rule_name': rule_name, 'extracted_value': str(extracted_value)
        })

    async def get_custom_extractions(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM custom_extractions WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_custom_search_match(self, audit_id: str, page_id: int, page_url: str, search_name: str, matched: bool, snippet: str = ""):
        await self._insert('custom_search_matches', {
            'audit_id': audit_id, 'page_id': page_id, 'page_url': page_url,
            'search_name': search_name, 'matched': matched, 'snippet': snippet
        })

    async def get_custom_search_matches(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM custom_search_matches WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_hreflang(self, audit_id: str, page_id: int, source_url: str, target_url: str, lang_code: str, is_reciprocal: bool = True, is_self: bool = False, error_type: Optional[str] = None):
        await self._insert('hreflang_tags', {
            'audit_id': audit_id, 'page_id': page_id, 'source_url': source_url,
            'target_url': target_url, 'lang_code': lang_code,
            'is_reciprocal': is_reciprocal, 'is_self': is_self, 'error_type': error_type
        })

    async def get_hreflang_tags(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM hreflang_tags WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_log_visit(self, audit_id: str, url: str, bot_type: str, ip_address: str, status_code: int, timestamp: str):
        await self._insert('log_visits', {
            'audit_id': audit_id, 'url': url, 'bot_type': bot_type,
            'ip_address': ip_address, 'status_code': status_code, 'timestamp': timestamp
        })

    async def get_log_visits(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM log_visits WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_gsc_data(self, audit_id: str, url: str, clicks: int, impressions: int, ctr: float, position: float):
        await self._insert('gsc_data', {
            'audit_id': audit_id, 'url': url, 'clicks': clicks,
            'impressions': impressions, 'ctr': ctr, 'position': position
        })

    async def get_gsc_data(self, audit_id: str) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT * FROM gsc_data WHERE audit_id = ?", (audit_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def update_page_pagerank(self, audit_id: str, page_id: int, pagerank: float):
        await self.conn.execute("UPDATE pages SET internal_pagerank = ? WHERE audit_id = ? AND id = ?", (pagerank, audit_id, page_id))
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None
