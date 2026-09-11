import logging
import httpx
from typing import Dict, Any, List, Optional
from database.db import Database

logger = logging.getLogger(__name__)

class GSCClient:
    """
    Client for Google Search Console API. Fetches URL-level performance metrics
    (Clicks, Impressions, CTR, Average Position) and correlates with audit data.
    """
    def __init__(self, db: Database, audit_id: str, access_token: Optional[str] = None):
        self.db = db
        self.audit_id = audit_id
        self.access_token = access_token

    async def fetch_and_store_performance(self, site_url: str, start_date: str = "28daysAgo", end_date: str = "today") -> Dict[str, Any]:
        if not self.access_token:
            logger.warning("GSC access token not provided. Skipping GSC data pull.")
            return {'error': 'No access token'}

        api_url = f"https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["page"],
            "rowLimit": 5000
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(api_url, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.error(f"GSC API error {resp.status_code}: {resp.text}")
                    return {'error': resp.text}

                data = resp.json()
                rows = data.get('rows', [])

                for row in rows:
                    page_url = row.get('keys', [''])[0]
                    clicks = int(row.get('clicks', 0))
                    impressions = int(row.get('impressions', 0))
                    ctr = float(row.get('ctr', 0.0))
                    position = float(row.get('position', 0.0))

                    await self.db.add_gsc_data(
                        audit_id=self.audit_id,
                        url=page_url,
                        clicks=clicks,
                        impressions=impressions,
                        ctr=ctr,
                        position=position
                    )

                    # Diagnostic 1: High Impressions, Low CTR (CTR Opportunity)
                    if impressions > 500 and ctr < 0.02 and position <= 15:
                        page = await self.db.get_page_by_url(self.audit_id, page_url)
                        page_id = page['id'] if page else None
                        await self.db.add_issue(
                            audit_id=self.audit_id,
                            page_id=page_id,
                            url=page_url,
                            category='onpage',
                            severity='warning',
                            issue_type='gsc_low_ctr_opportunity',
                            message=f"High Search Impressions ({impressions}) with low CTR ({round(ctr*100, 2)}%) at avg position {round(position, 1)}",
                            recommendation="Rewrite title tag and meta description with compelling hooks and search intent match to boost click-through rate.",
                            element=page_url
                        )

                return {'rows_ingested': len(rows)}
        except Exception as e:
            logger.error(f"Failed to fetch GSC performance: {e}")
            return {'error': str(e)}
