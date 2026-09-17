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
        new_page_columns = [
            ("viewport", "TEXT"),
            ("parent_url", "TEXT"),
            ("language", "TEXT"),
            ("robots_meta", "TEXT"),
            ("page_type", "TEXT"),
            ("mime_type", "TEXT"),
            ("title_length", "INTEGER"),
            ("title_pixel_width", "INTEGER"),
            ("meta_description_length", "INTEGER"),
            ("meta_desc_pixel_width", "INTEGER"),
            ("meta_keywords", "TEXT"),
            ("meta_keywords_length", "INTEGER"),
            ("h1_count", "INTEGER DEFAULT 0"),
            ("h1_length", "INTEGER"),
            ("h2_count", "INTEGER DEFAULT 0"),
            ("h2_length", "INTEGER"),
            ("sentence_count", "INTEGER"),
            ("avg_words_per_sentence", "REAL"),
            ("text_ratio", "REAL"),
            ("flesch_reading_ease", "REAL"),
            ("readability_label", "TEXT"),
            ("folder_depth", "INTEGER"),
            ("http_version", "TEXT"),
            ("mobile_alt_link", "TEXT"),
            ("size_bytes", "INTEGER"),
            ("transferred_bytes", "INTEGER"),
            ("total_transferred_bytes", "INTEGER"),
            ("redirect_type", "TEXT"),
            ("unique_inlinks", "INTEGER DEFAULT 0"),
            ("unique_outlinks", "INTEGER DEFAULT 0"),
            ("unique_external_outlinks", "INTEGER DEFAULT 0"),
            ("link_score", "REAL DEFAULT 0.0"),
            ("headers_json", "TEXT"),
            ("cookies_json", "TEXT"),
            ("content_near_duplicate_hash", "TEXT"),
            ("near_duplicate_count", "INTEGER DEFAULT 0"),
            ("closest_duplicate_url", "TEXT"),
            ("closest_duplicate_similarity", "REAL"),
            ("psi_status", "TEXT"),
            ("psi_mobile_score", "REAL"),
            ("psi_desktop_score", "REAL"),
            ("accessibility_violations_total", "INTEGER DEFAULT 0"),
            ("accessibility_best_practice", "INTEGER DEFAULT 0"),
            ("accessibility_wcag_2_0_a", "INTEGER DEFAULT 0"),
            ("accessibility_wcag_2_0_aa", "INTEGER DEFAULT 0"),
            ("accessibility_wcag_2_0_aaa", "INTEGER DEFAULT 0"),
            ("accessibility_wcag_2_1_aa", "INTEGER DEFAULT 0"),
            ("accessibility_wcag_2_2_aa", "INTEGER DEFAULT 0"),
            ("crawl_timestamp", "TIMESTAMP"),
            ("html_word_count", "INTEGER"),
            ("rendered_word_count", "INTEGER"),
            ("word_count_change", "INTEGER"),
            ("js_word_count_pct", "REAL"),
            ("html_title", "TEXT"),
            ("rendered_title", "TEXT"),
            ("html_h1", "TEXT"),
            ("rendered_h1", "TEXT"),
            ("html_meta_description", "TEXT"),
            ("rendered_meta_description", "TEXT"),
            ("html_canonical", "TEXT"),
            ("rendered_canonical", "TEXT"),
            ("html_meta_robots", "TEXT"),
            ("rendered_meta_robots", "TEXT"),
            ("js_errors", "INTEGER DEFAULT 0"),
            ("js_warnings", "INTEGER DEFAULT 0"),
            ("js_info", "INTEGER DEFAULT 0"),
            ("js_debug", "INTEGER DEFAULT 0"),
            ("js_issues", "TEXT"),
            ("pretty_url", "TEXT"),
            ("ugly_url", "TEXT"),
            ("x_robots_tag", "TEXT"),
            ("http_canonical", "TEXT"),
            ("amp_html_link", "TEXT"),
        ]
        for col, col_type in new_page_columns:
            try:
                await self.conn.execute(f"ALTER TABLE pages ADD COLUMN {col} {col_type};")
            except Exception:
                pass

        for col, col_type in [
            ("unique_js_inlinks", "INTEGER DEFAULT 0"),
            ("unique_js_outlinks", "INTEGER DEFAULT 0"),
        ]:
            try:
                await self.conn.execute(f"ALTER TABLE links ADD COLUMN {col} {col_type};")
            except Exception:
                pass
        await self.conn.commit()

        try:
            from .migrations import run_migrations
            await run_migrations(self.conn)
        except Exception as e:
            logger.warning(f"Database migrations error: {e}")

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
        return cursor.lastrowid

    async def flush(self):
        """Commit pending writes to disk."""
        if self.conn:
            await self.conn.commit()

    async def create_audit(self, audit_id: str, domain: str, url: str, config: str = "{}") -> str:
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

    async def get_issues(self, audit_id: str, category: Optional[str] = None, severity: Optional[str] = None, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM issues WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
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

    async def get_links(self, audit_id: str, is_internal: Optional[bool] = None, is_broken: Optional[bool] = None, page_id: Optional[int] = None, source_page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM links WHERE audit_id = ?"
        params = [audit_id]
        if is_internal is not None:
            query += " AND is_internal = ?"
            params.append(is_internal)
        if is_broken is not None:
            query += " AND is_broken = ?"
            params.append(is_broken)
        sp_id = page_id if page_id is not None else source_page_id
        if sp_id is not None:
            query += " AND source_page_id = ?"
            params.append(sp_id)
            
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def get_page_inlinks(self, audit_id: str, target_url: str, limit: int = 100) -> List[Dict[str, Any]]:
        norm_url = target_url.rstrip('/')
        query = """
            SELECT source_url, anchor_text, is_internal, status_code, nofollow
            FROM links
            WHERE audit_id = ? AND (target_url = ? OR target_url = ?)
            LIMIT ?
        """
        async with self.conn.execute(query, (audit_id, target_url, norm_url, limit)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def get_page_outlinks(self, audit_id: str, source_page_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        query = """
            SELECT target_url, anchor_text, is_internal, status_code, nofollow
            FROM links
            WHERE audit_id = ? AND source_page_id = ?
            LIMIT ?
        """
        async with self.conn.execute(query, (audit_id, source_page_id, limit)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def get_incoming_link_targets(self, audit_id: str) -> set:
        query = "SELECT DISTINCT target_url FROM links WHERE audit_id = ? AND is_internal = 1"
        async with self.conn.execute(query, (audit_id,)) as cursor:
            rows = await cursor.fetchall()
            targets = set()
            for r in rows:
                if r[0]:
                    targets.add(r[0])
                    targets.add(r[0].rstrip('/'))
            return targets

    async def update_link(self, link_id: int, **kwargs):
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [link_id]
        await self.conn.execute(f"UPDATE links SET {set_clause} WHERE id = ?", values)
        await self.conn.commit()

    async def update_links_status_batch(self, updates_list: List[tuple]):
        """Batch update (status_code, is_broken, link_id) for high performance."""
        if not updates_list:
            return
        query = "UPDATE links SET status_code = ?, is_broken = ? WHERE id = ?"
        await self.conn.executemany(query, updates_list)
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

    async def get_images(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM images WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
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

    async def get_headings(self, page_id: Optional[int] = None, audit_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if audit_id is not None:
            query = "SELECT h.* FROM headings h JOIN pages p ON h.page_id = p.id WHERE p.audit_id = ?"
            params = [audit_id]
            if page_id is not None:
                query += " AND h.page_id = ?"
                params.append(page_id)
            query += " ORDER BY h.page_id, h.order_index"
        elif page_id is not None:
            query = "SELECT * FROM headings WHERE page_id = ? ORDER BY order_index"
            params = [page_id]
        else:
            query = "SELECT * FROM headings ORDER BY order_index"
            params = []
        async with self.conn.execute(query, params) as cursor:
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

    async def get_structured_data(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM structured_data WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
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

    async def get_hreflang_tags(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM hreflang_tags WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
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

    async def update_pages_pagerank_batch(self, pr_updates: List[tuple]):
        """Batch update (pagerank, audit_id, page_id) in a single transaction."""
        if not pr_updates:
            return
        await self.conn.executemany("UPDATE pages SET internal_pagerank = ? WHERE audit_id = ? AND id = ?", pr_updates)
        await self.conn.commit()

    async def update_page_columns(self, page_id: int, **kwargs):
        if not kwargs:
            return
        set_clauses = [f"{k} = ?" for k in kwargs.keys()]
        values = list(kwargs.values()) + [page_id]
        query = f"UPDATE pages SET {', '.join(set_clauses)} WHERE id = ?"
        await self.conn.execute(query, values)

    async def add_pagination_tag(self, audit_id: str, page_id: int, page_url: str, rel_type: str, target_url: str, source: str = "html"):
        await self._insert('pagination_tags', {
            'audit_id': audit_id, 'page_id': page_id, 'page_url': page_url,
            'rel_type': rel_type, 'target_url': target_url, 'source': source
        })

    async def add_pagination_tags_batch(self, tags: List[Dict[str, Any]]):
        if not tags:
            return
        rows = [
            (t.get('audit_id'), t.get('page_id'), t.get('page_url'), t.get('rel_type'), t.get('target_url'), t.get('source'))
            for t in tags
        ]
        await self.conn.executemany(
            "INSERT INTO pagination_tags (audit_id, page_id, page_url, rel_type, target_url, source) VALUES (?, ?, ?, ?, ?, ?)",
            rows
        )

    async def get_pagination_tags(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if page_id is not None:
            query = "SELECT * FROM pagination_tags WHERE audit_id = ? AND page_id = ?"
            args = (audit_id, page_id)
        else:
            query = "SELECT * FROM pagination_tags WHERE audit_id = ?"
            args = (audit_id,)
        async with self.conn.execute(query, args) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_accessibility_violation(self, audit_id: str, page_id: int, page_url: str, rule_id: str, description: str, impact: str, wcag_tags: str, html_snippet: str = "", target_selector: str = ""):
        await self._insert('accessibility_violations', {
            'audit_id': audit_id, 'page_id': page_id, 'page_url': page_url,
            'rule_id': rule_id, 'description': description, 'impact': impact,
            'wcag_tags': wcag_tags, 'html_snippet': html_snippet, 'target_selector': target_selector
        })

    async def add_accessibility_violations_batch(self, violations: List[Dict[str, Any]]):
        if not violations:
            return
        rows = [
            (v.get('audit_id'), v.get('page_id'), v.get('page_url'), v.get('rule_id'),
             v.get('description'), v.get('impact'), v.get('wcag_tags'), v.get('html_snippet'), v.get('target_selector'))
            for v in violations
        ]
        await self.conn.executemany(
            "INSERT INTO accessibility_violations (audit_id, page_id, page_url, rule_id, description, impact, wcag_tags, html_snippet, target_selector) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows
        )

    async def get_accessibility_violations(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if page_id is not None:
            query = "SELECT * FROM accessibility_violations WHERE audit_id = ? AND page_id = ?"
            args = (audit_id, page_id)
        else:
            query = "SELECT * FROM accessibility_violations WHERE audit_id = ?"
            args = (audit_id,)
        async with self.conn.execute(query, args) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_console_log(self, audit_id: str, page_id: int, page_url: str, level: str, message: str, source: str = "javascript", line_number: Optional[int] = None, timestamp: Optional[str] = None):
        await self._insert('console_logs', {
            'audit_id': audit_id, 'page_id': page_id, 'page_url': page_url,
            'level': level, 'message': message, 'source': source,
            'line_number': line_number, 'timestamp': timestamp
        })

    async def add_console_logs_batch(self, logs: List[Dict[str, Any]]):
        if not logs:
            return
        rows = [
            (l.get('audit_id'), l.get('page_id'), l.get('page_url'), l.get('level'),
             l.get('message'), l.get('source'), l.get('line_number'), l.get('timestamp'))
            for l in logs
        ]
        await self.conn.executemany(
            "INSERT INTO console_logs (audit_id, page_id, page_url, level, message, source, line_number, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows
        )

    async def get_console_logs(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if page_id is not None:
            query = "SELECT * FROM console_logs WHERE audit_id = ? AND page_id = ?"
            args = (audit_id, page_id)
        else:
            query = "SELECT * FROM console_logs WHERE audit_id = ?"
            args = (audit_id,)
        async with self.conn.execute(query, args) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_sitemap_entry(self, audit_id: str, page_id: Optional[int], page_url: str, sitemap_url: str, lastmod: Optional[str] = None, changefreq: Optional[str] = None, priority: Optional[float] = None):
        await self._insert('sitemap_entries', {
            'audit_id': audit_id, 'page_id': page_id, 'page_url': page_url,
            'sitemap_url': sitemap_url, 'lastmod': lastmod, 'changefreq': changefreq,
            'priority': priority
        })

    async def add_sitemap_entries_batch(self, entries: List[Dict[str, Any]]):
        if not entries:
            return
        rows = [
            (e.get('audit_id'), e.get('page_id'), e.get('page_url'), e.get('sitemap_url'),
             e.get('lastmod'), e.get('changefreq'), e.get('priority'))
            for e in entries
        ]
        await self.conn.executemany(
            "INSERT INTO sitemap_entries (audit_id, page_id, page_url, sitemap_url, lastmod, changefreq, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows
        )

    async def get_sitemap_entries(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if page_id is not None:
            query = "SELECT * FROM sitemap_entries WHERE audit_id = ? AND page_id = ?"
            args = (audit_id, page_id)
        else:
            query = "SELECT * FROM sitemap_entries WHERE audit_id = ?"
            args = (audit_id,)
        async with self.conn.execute(query, args) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def get_near_duplicates(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT id, url, content_near_duplicate_hash, near_duplicate_count, closest_duplicate_url, closest_duplicate_similarity FROM pages WHERE audit_id = ? AND near_duplicate_count > 0"
        params = [audit_id]
        if page_id is not None:
            query += " AND id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_frontier_batch(self, entries: List[Dict[str, Any]]):
        """Batch insert discovered URLs into the persistent crawl frontier."""
        if not entries:
            return
        rows = [
            (
                e.get('audit_id'),
                e.get('url'),
                e.get('depth', 0),
                e.get('parent_url'),
                e.get('status', 'pending'),
                e.get('created_at')
            )
            for e in entries
        ]
        await self.conn.executemany(
            """INSERT OR IGNORE INTO crawl_frontier 
               (audit_id, url, depth, parent_url, status, created_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            rows
        )

    async def pop_frontier_batch(self, audit_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Atomically fetch and claim the next batch of pending URLs from frontier ordered by depth."""
        async with self.conn.execute(
            """SELECT id, url, depth, parent_url 
               FROM crawl_frontier 
               WHERE audit_id = ? AND status = 'pending' 
               ORDER BY depth ASC, id ASC 
               LIMIT ?""",
            (audit_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            
        if not rows:
            return []
            
        ids = [row['id'] for row in rows]
        placeholders = ', '.join(['?'] * len(ids))
        await self.conn.execute(
            f"UPDATE crawl_frontier SET status = 'in_flight' WHERE id IN ({placeholders})",
            ids
        )
        return [dict(row) for row in rows]

    async def mark_frontier_status(self, audit_id: str, url: str, status: str):
        """Update frontier URL status (e.g. 'done', 'failed')."""
        await self.conn.execute(
            "UPDATE crawl_frontier SET status = ? WHERE audit_id = ? AND url = ?",
            (status, audit_id, url)
        )

    async def mark_frontier_status_batch(self, audit_id: str, urls: List[str], status: str):
        """Update status for multiple URLs in the crawl frontier."""
        if not urls:
            return
        placeholders = ', '.join(['?'] * len(urls))
        await self.conn.execute(
            f"UPDATE crawl_frontier SET status = ? WHERE audit_id = ? AND url IN ({placeholders})",
            [status, audit_id] + urls
        )

    async def get_frontier_count(self, audit_id: str, status: Optional[str] = None) -> int:
        """Get count of URLs in frontier, optionally filtered by status."""
        if status:
            query = "SELECT COUNT(*) FROM crawl_frontier WHERE audit_id = ? AND status = ?"
            args = (audit_id, status)
        else:
            query = "SELECT COUNT(*) FROM crawl_frontier WHERE audit_id = ?"
            args = (audit_id,)
        async with self.conn.execute(query, args) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def add_forms_batch(self, forms_list: List[Dict[str, Any]]):
        if not forms_list:
            return
        query = """
            INSERT INTO forms (audit_id, page_id, page_url, action_url, method, form_id, has_password, is_search, is_insecure, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        params = [
            (
                f.get('audit_id'), f.get('page_id'), f.get('page_url'), f.get('action_url'),
                f.get('method', 'GET'), f.get('form_id'), f.get('has_password', False),
                f.get('is_search', False), f.get('is_insecure', False), now
            )
            for f in forms_list
        ]
        await self.conn.executemany(query, params)

    async def get_forms(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM forms WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def add_external_links_batch(self, links_list: List[Dict[str, Any]]):
        if not links_list:
            return
        query = """
            INSERT INTO external_links (audit_id, source_page_id, source_url, target_url, anchor_text, rel_attributes, status_code, is_broken, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        params = [
            (
                l.get('audit_id'), l.get('source_page_id'), l.get('source_url'), l.get('target_url'),
                l.get('anchor_text'), l.get('rel_attributes'), l.get('status_code'),
                l.get('is_broken', False), now
            )
            for l in links_list
        ]
        await self.conn.executemany(query, params)

    async def get_external_links(self, audit_id: str, page_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM external_links WHERE audit_id = ?"
        params = [audit_id]
        if page_id is not None:
            query += " AND source_page_id = ?"
            params.append(page_id)
        async with self.conn.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def update_image_size(self, image_id: int, file_size: int, is_broken: bool = False):
        await self.conn.execute(
            "UPDATE images SET file_size = ?, is_broken = ? WHERE id = ?",
            (file_size, is_broken, image_id)
        )

    async def update_resource_size(self, resource_id: int, size: int):
        await self.conn.execute(
            "UPDATE resources SET size = ? WHERE id = ?",
            (size, resource_id)
        )

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

