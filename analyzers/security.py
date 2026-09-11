import logging
import urllib.parse
from typing import Optional, Any
from database.db import Database

logger = logging.getLogger(__name__)

class SecurityAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting security analysis for audit {self.audit_id}")
        
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        http_pages_count = 0

        for page in pages:
            page_id = page.get('id')
            url = page.get('url')
            
            if not url:
                continue

            parsed_url = urllib.parse.urlparse(url)
            is_https = parsed_url.scheme == 'https'

            if not is_https:
                await self._add_issue(page_id, url, 'critical', 'http_page', "Page is served over HTTP", "Migrate the page to HTTPS to secure user data and improve SEO.", url)
                http_pages_count += 1
            else:
                # Check for mixed content
                resources = await self.db.get_resources(self.audit_id, page_id)
                mixed_content = False
                for res in resources:
                    res_url = res.get('url')
                    if res_url and urllib.parse.urlparse(res_url).scheme == 'http':
                        await self._add_issue(page_id, url, 'critical', 'mixed_content', "Mixed content: HTTPS page loading HTTP resources", f"Change resource URL to HTTPS: {res_url}", res_url)
                        mixed_content = True

        if http_pages_count > 0:
            await self._add_issue(None, None, 'critical', 'site_wide_http', f"Site has {http_pages_count} HTTP pages", "Enforce site-wide HTTPS and HSTS.", http_pages_count)
        else:
            await self._add_issue(None, None, 'info', 'site_wide_https', "All pages are served over HTTPS", "Great job securing the site.", None)

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='security',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
