import json
import logging
import urllib.parse
from typing import Optional, Any
from database.db import Database
from services.security_inspector import (
    check_hsts_sync,
    check_mixed_content_sync,
    check_unsafe_links_sync,
    check_plaintext_emails_sync
)

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
        missing_hsts_count = 0

        for page in pages:
            page_id = page.get('id')
            url = page.get('url')
            
            if not url:
                continue

            parsed_url = urllib.parse.urlparse(url)
            is_https = parsed_url.scheme == 'https'

            # Parse headers for this page
            headers = {}
            headers_json = page.get('headers_json')
            if headers_json:
                try:
                    headers = json.loads(headers_json)
                except Exception:
                    headers = {}

            if not is_https:
                await self._add_issue(page_id, url, 'critical', 'http_page', "Page is served over HTTP", "Migrate the page to HTTPS to secure user data and improve SEO.", url)
                http_pages_count += 1
            else:
                # Check HSTS
                hsts_res = check_hsts_sync(headers, url)
                if not hsts_res.get('passed'):
                    missing_hsts_count += 1
                    await self._add_issue(page_id, url, 'warning', 'missing_hsts', "Strict-Transport-Security (HSTS) header is missing", "Add Strict-Transport-Security header (e.g. max-age=31536000; includeSubDomains; preload) to enforce HTTPS.", url)

                # Check for mixed content in resources
                resources = await self.db.get_resources(self.audit_id, page_id)
                for res in resources:
                    res_url = res.get('url')
                    if res_url and urllib.parse.urlparse(res_url).scheme == 'http':
                        await self._add_issue(page_id, url, 'critical', 'mixed_content', "Mixed content: HTTPS page loading HTTP resources", f"Change resource URL to HTTPS: {res_url}", res_url)

                # Check for mixed content in images
                images = await self.db.get_images(self.audit_id, page_id=page_id)
                for img in images:
                    img_src = img.get('src')
                    if img_src and urllib.parse.urlparse(img_src).scheme == 'http':
                        await self._add_issue(page_id, url, 'critical', 'mixed_content', "Mixed content: HTTPS page loading HTTP image", f"Update image source to HTTPS: {img_src}", img_src)

            # Check external links for reverse tabnabbing (rel="noopener noreferrer")
            links = await self.db.get_links(self.audit_id, page_id=page_id, is_internal=False)
            for link in links:
                rel = (link.get('rel_attribute') or '').lower()
                target_u = link.get('target_url') or ''
                if target_u.startswith(('http://', 'https://')):
                    if 'noopener' not in rel and 'noreferrer' not in rel:
                        await self._add_issue(
                            page_id, url, 'warning', 'unsafe_external_link',
                            f"External link without rel='noopener' or rel='noreferrer': {target_u}",
                            "Add rel='noopener noreferrer' to external links to prevent reverse tabnabbing and window.opener hijacking.",
                            target_u
                        )

        if http_pages_count > 0:
            await self._add_issue(None, None, 'critical', 'site_wide_http', f"Site has {http_pages_count} HTTP pages", "Enforce site-wide HTTPS and HSTS.", http_pages_count)
        else:
            await self._add_issue(None, None, 'info', 'site_wide_https', "All pages are served over HTTPS", "Great job securing the site.", None)

        if missing_hsts_count > 0:
            await self._add_issue(None, None, 'warning', 'site_wide_missing_hsts', f"{missing_hsts_count} pages lack HSTS headers", "Configure HSTS server-wide with includeSubDomains and preload directives.", missing_hsts_count)

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

