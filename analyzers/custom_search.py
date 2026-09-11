import logging
from typing import Dict, Any, List
from database.db import Database

logger = logging.getLogger(__name__)

class CustomSearchAnalyzer:
    """
    Evaluates custom source code search rules (Contains / Does Not Contain)
    and registers matching issues into the audit issues database.
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting Custom Search evaluation for audit {self.audit_id}")
        matches = await self.db.get_custom_search_matches(self.audit_id)
        if not matches:
            return

        for match in matches:
            if not match.get('matched', False):
                continue

            rule_name = match.get('search_name', 'Custom Search')
            url = match.get('page_url', '')
            page_id = match.get('page_id')
            snippet = match.get('snippet', '')

            await self.db.add_issue(
                audit_id=self.audit_id,
                page_id=page_id,
                url=url,
                category='technical',
                severity='warning',
                issue_type='custom_search_match',
                message=f"Custom Search Rule Alert: '{rule_name}' triggered",
                recommendation=f"Review page source to resolve search condition '{rule_name}'.",
                element=snippet or url
            )

        logger.info(f"Custom Search evaluation completed for audit {self.audit_id}")
