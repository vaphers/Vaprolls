import logging
import json
from typing import Optional, Any
from database.db import Database

logger = logging.getLogger(__name__)

class StructuredDataAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting structured data analysis for audit {self.audit_id}")
        
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        structured_data_list = await self.db.get_structured_data(self.audit_id)
        sd_by_page = {}
        for sd in structured_data_list:
            sd_by_page.setdefault(sd.get('page_id'), []).append(sd)

        pages_with_sd = 0
        schema_types_count = {}

        for page in pages:
            page_id = page.get('id')
            url = page.get('url')
            
            page_sds = sd_by_page.get(page_id, [])
            
            if not page_sds:
                await self._add_issue(page_id, url, 'info', 'no_structured_data', "No structured data found", "Implement structured data (e.g., JSON-LD) to enhance search engine understanding.", None)
            else:
                pages_with_sd += 1
                for sd in page_sds:
                    is_valid = sd.get('is_valid')
                    data_json = sd.get('data_json')
                    schema_type = sd.get('schema_type', 'Unknown')
                    
                    if schema_type:
                        schema_types_count[schema_type] = schema_types_count.get(schema_type, 0) + 1

                    if is_valid is False:
                        errors = sd.get('errors', 'Invalid JSON-LD format')
                        await self._add_issue(page_id, url, 'critical', 'invalid_json_ld', f"Invalid JSON-LD: {errors}", "Fix JSON-LD syntax errors.", None)
                        continue

                    if not data_json:
                        continue
                        
                    try:
                        data = json.loads(data_json)
                    except json.JSONDecodeError:
                        continue

                    if isinstance(data, dict):
                        self._validate_schema_object(data, page_id, url)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                self._validate_schema_object(item, page_id, url)

        # Site-wide checks
        total_pages = len(pages)
        if total_pages > 0:
            coverage = (pages_with_sd / total_pages) * 100
            await self._add_issue(None, None, 'info', 'schema_coverage', f"Schema coverage: {coverage:.1f}% of pages have structured data", "Increase structured data coverage where applicable.", coverage)
            
            if pages_with_sd == 0:
                await self._add_issue(None, None, 'warning', 'no_schema_markup', "No schema.org markup found on the entire site", "Implement structured data sitewide.", None)
            
            if schema_types_count:
                await self._add_issue(None, None, 'info', 'schema_distribution', "Schema types distribution", "Review schema types used across the site.", schema_types_count)


    def _validate_schema_object(self, data: dict, page_id: int, url: str):
        context = data.get('@context')
        if not context:
            # We can't await inside sync method, so we should make this async or collect and await later.
            # Let's just store a task or rewrite this to be async.
            pass
            
    # Need to be async
    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='structured_data',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
