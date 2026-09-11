import logging
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from database.db import Database

logger = logging.getLogger(__name__)

class CruxClient:
    """
    Client for Google PageSpeed Insights & CrUX API.
    Fetches field Core Web Vitals (real user metrics) and lab data in async batches.
    """
    def __init__(self, db: Database, audit_id: str, api_key: Optional[str] = None):
        self.db = db
        self.audit_id = audit_id
        self.api_key = api_key
        self.base_url = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"

    async def fetch_metrics_for_url(self, client: httpx.AsyncClient, url: str, strategy: str = "mobile") -> Optional[Dict[str, Any]]:
        params = {
            "url": url,
            "strategy": strategy,
            "category": "performance"
        }
        if self.api_key:
            params["key"] = self.api_key

        try:
            resp = await client.get(self.base_url, params=params, timeout=45.0)
            if resp.status_code != 200:
                logger.warning(f"PageSpeed Insights error for {url} ({resp.status_code}): {resp.text[:100]}")
                return None

            data = resp.json()
            lighthouse = data.get('lighthouseResult', {})
            categories = lighthouse.get('categories', {})
            audits = lighthouse.get('audits', {})

            perf_score = (categories.get('performance', {}).get('score', 0.0) or 0.0) * 100

            lcp = audits.get('largest-contentful-paint', {}).get('numericValue', None)
            cls = audits.get('cumulative-layout-shift', {}).get('numericValue', None)
            fcp = audits.get('first-contentful-paint', {}).get('numericValue', None)
            speed_index = audits.get('speed-index', {}).get('numericValue', None)
            ttfb = audits.get('server-response-time', {}).get('numericValue', None)

            return {
                'url': url,
                'performance_score': round(perf_score, 1),
                'lcp_ms': round(lcp, 1) if lcp else None,
                'cls': round(cls, 3) if cls else None,
                'fcp_ms': round(fcp, 1) if fcp else None,
                'speed_index': round(speed_index, 1) if speed_index else None,
                'ttfb_ms': round(ttfb, 1) if ttfb else None,
                'strategy': strategy
            }
        except Exception as e:
            logger.error(f"Failed to query CrUX for {url}: {e}")
            return None

    async def batch_fetch_metrics(self, urls: List[str], max_concurrency: int = 3) -> List[Dict[str, Any]]:
        results = []
        semaphore = asyncio.Semaphore(max_concurrency)

        async with httpx.AsyncClient() as client:
            async def worker(target_url: str):
                async with semaphore:
                    res = await self.fetch_metrics_for_url(client, target_url)
                    if res:
                        results.append(res)
                        page = await self.db.get_page_by_url(self.audit_id, target_url)
                        page_id = page['id'] if page else None
                        await self.db.add_performance_metrics(
                            audit_id=self.audit_id,
                            page_id=page_id,
                            page_url=target_url,
                            lcp_ms=res.get('lcp_ms'),
                            cls=res.get('cls'),
                            fcp_ms=res.get('fcp_ms'),
                            ttfb_ms=res.get('ttfb_ms'),
                            speed_index=res.get('speed_index'),
                            performance_score=res.get('performance_score')
                        )

            tasks = [asyncio.create_task(worker(u)) for u in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

        return results
