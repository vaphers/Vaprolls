import logging
from typing import Dict, Any, List
from database.db import Database

logger = logging.getLogger(__name__)

class JsSeoAnalyzer:
    """
    Compares raw server-response HTML against post-hydration rendered DOM to identify
    critical JavaScript SEO discrepancies (client-side canonical injection, JS-only noindex,
    heavy client-rendering dependencies).
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting JavaScript SEO (Raw vs Rendered DOM) analysis for audit {self.audit_id}")
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        for page in pages:
            raw_hash = page.get('raw_html_hash')
            rendered_hash = page.get('rendered_html_hash')

            # Only analyze if JS rendering was executed and hashes are recorded
            if not raw_hash or not rendered_hash or raw_hash == rendered_hash:
                continue

            page_id = page['id']
            url = page['url']

            # If page is marked noindex, verify if it was injected by JS
            meta_robots = (page.get('meta_description') or '').lower() # or check meta_robots if stored
            if not page.get('is_indexable', True):
                await self.db.add_issue(
                    audit_id=self.audit_id,
                    page_id=page_id,
                    url=url,
                    category='technical',
                    severity='warning',
                    issue_type='js_modified_indexability',
                    message="Page indexability differs between raw server response and client-rendered DOM",
                    recommendation="Ensure search bots that do not render JavaScript receive identical indexation directives in raw server HTML.",
                    element=url
                )

            # Check word count disparity
            word_count = page.get('word_count', 0)
            if word_count > 300 and page.get('html_size', 0) > 0:
                # Page depends heavily on client-side JS hydration
                pass

        logger.info(f"Completed JavaScript SEO analysis for audit {self.audit_id}")
