import logging
from typing import Optional, Any
from database.db import Database
import json

logger = logging.getLogger(__name__)

class MobileAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting mobile analysis for audit {self.audit_id}")
        
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        pages_without_viewport = 0

        for page in pages:
            page_id = page.get('id')
            url = page.get('url')
            
        # Check if any pages have viewport data populated
        any_viewport_tracked = any(page.get('viewport') is not None for page in pages)

        for page in pages:
            page_id = page.get('id')
            url = page.get('url')
            viewport = page.get('viewport')

            if viewport is None:
                if any_viewport_tracked:
                    # Explicitly missing on this page while tracked on others
                    await self._add_issue(page_id, url, 'critical', 'missing_viewport', "Missing meta viewport tag", "Add <meta name='viewport' content='width=device-width, initial-scale=1'> to the head of the page.", None)
                    pages_without_viewport += 1
            else:
                viewport_lower = str(viewport).lower()
                if 'width=device-width' not in viewport_lower:
                    await self._add_issue(page_id, url, 'warning', 'invalid_viewport_width', "Viewport not set to device-width", "Set viewport width to device-width for proper mobile scaling.", viewport)
                
                if 'maximum-scale=1' in viewport_lower or 'user-scalable=no' in viewport_lower:
                    await self._add_issue(page_id, url, 'warning', 'viewport_zoom_disabled', "Prevents zooming, bad for accessibility", "Remove maximum-scale=1 and user-scalable=no from viewport meta tag.", viewport)

        if pages_without_viewport > 0:
            await self._add_issue(None, None, 'critical', 'site_wide_missing_viewport', f"{pages_without_viewport} pages missing viewport tag", "Ensure all pages have a proper meta viewport tag.", pages_without_viewport)

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='mobile',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
