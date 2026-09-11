import logging
import re
from typing import Dict, Any, List, Optional
from database.db import Database

logger = logging.getLogger(__name__)

# Combined Log Format: 127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://..." "Mozilla/..."
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+[^"]*"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)\s+"(?P<referrer>[^"]*)"\s+"(?P<agent>[^"]*)"'
)

BOT_SIGNATURES = {
    'Googlebot Smartphone': re.compile(r'Googlebot.*Mobile', re.I),
    'Googlebot Desktop': re.compile(r'Googlebot(?!.*Mobile)', re.I),
    'Bingbot': re.compile(r'bingbot', re.I),
    'YandexBot': re.compile(r'YandexBot', re.I),
    'Baiduspider': re.compile(r'Baiduspider', re.I),
    'DuckDuckBot': re.compile(r'DuckDuckBot', re.I),
}

class LogFileAnalyzer:
    """
    Ingests Apache/Nginx/Cloudflare web server access logs, identifies search bot crawl events,
    correlates log visits against audited URLs, and identifies crawl budget waste and orphan bot targets.
    """
    def __init__(self, db: Database, audit_id: str, log_file_path: str):
        self.db = db
        self.audit_id = audit_id
        self.log_file_path = log_file_path

    def identify_bot(self, user_agent: str) -> Optional[str]:
        for bot_name, pattern in BOT_SIGNATURES.items():
            if pattern.search(user_agent):
                return bot_name
        return None

    async def ingest_and_analyze(self) -> Dict[str, Any]:
        logger.info(f"Ingesting access log file: {self.log_file_path}")
        
        bot_hits_by_url: Dict[str, int] = {}
        bot_hits_by_status: Dict[int, int] = {}
        total_bot_hits = 0

        audit = await self.db.get_audit(self.audit_id)
        domain = audit.get('domain', '') if audit else ''

        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    match = LOG_PATTERN.match(line.strip())
                    if not match:
                        continue

                    agent = match.group('agent')
                    bot_name = self.identify_bot(agent)
                    if not bot_name:
                        continue

                    path = match.group('path')
                    status = int(match.group('status'))
                    ip = match.group('ip')
                    time_str = match.group('time')

                    total_bot_hits += 1
                    bot_hits_by_status[status] = bot_hits_by_status.get(status, 0) + 1
                    bot_hits_by_url[path] = bot_hits_by_url.get(path, 0) + 1

                    await self.db.add_log_visit(
                        audit_id=self.audit_id,
                        url=path,
                        bot_type=bot_name,
                        ip_address=ip,
                        status_code=status,
                        timestamp=time_str
                    )
        except Exception as e:
            logger.error(f"Failed to read access log file: {e}")
            return {'error': str(e)}

        pages = await self.db.get_pages(self.audit_id)
        crawled_paths = set()
        for p in pages:
            from urllib.parse import urlparse
            p_path = urlparse(p['url']).path or '/'
            crawled_paths.add(p_path)

        # 1. Crawl Budget Waste: Bot visits to 4xx/5xx pages
        broken_bot_hits = sum(count for status, count in bot_hits_by_status.items() if status >= 400)
        if broken_bot_hits > 0:
            await self.db.add_issue(
                audit_id=self.audit_id,
                page_id=None,
                url=domain,
                category='technical',
                severity='critical',
                issue_type='crawl_budget_waste_errors',
                message=f"Search bots hit {broken_bot_hits} error URLs (4xx/5xx), wasting crawl budget",
                recommendation="Fix or redirect broken URLs that search bots are actively crawling.",
                element=f"Total Error Hits: {broken_bot_hits}"
            )

        # 2. Orphan Bot Hits: URLs visited by bots but not linked in the internal structure
        orphan_bot_paths = [path for path in bot_hits_by_url if path not in crawled_paths and not path.endswith(('.jpg', '.png', '.css', '.js'))]
        if orphan_bot_paths:
            await self.db.add_issue(
                audit_id=self.audit_id,
                page_id=None,
                url=domain,
                category='technical',
                severity='warning',
                issue_type='orphan_urls_visited_by_bots',
                message=f"Search bots visited {len(orphan_bot_paths)} orphan URLs that have no internal links on the site",
                recommendation="Review orphan URLs visited by bots. Either link them internally if valuable or return 410 Gone / 301 Redirect.",
                element=', '.join(orphan_bot_paths[:5])
            )

        # 3. Never-crawled core pages
        unvisited_core_pages = [p['url'] for p in pages if (urlparse(p['url']).path or '/') not in bot_hits_by_url and p.get('crawl_depth', 0) <= 2]
        if unvisited_core_pages:
            await self.db.add_issue(
                audit_id=self.audit_id,
                page_id=None,
                url=domain,
                category='technical',
                severity='info',
                issue_type='unvisited_core_pages',
                message=f"{len(unvisited_core_pages)} important pages have received 0 search bot visits in the log period",
                recommendation="Boost internal linking from frequently crawled pages or submit these URLs via XML sitemaps to prompt bot crawls.",
                element=', '.join(unvisited_core_pages[:5])
            )

        return {
            'total_bot_hits': total_bot_hits,
            'hits_by_status': bot_hits_by_status,
            'top_crawled_urls': sorted(bot_hits_by_url.items(), key=lambda x: x[1], reverse=True)[:20],
            'orphan_bot_urls': orphan_bot_paths[:20],
            'unvisited_core_pages': unvisited_core_pages[:20]
        }
