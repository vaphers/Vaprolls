import logging
from typing import Optional, Any
from database.db import Database
import urllib.parse
import httpx
import time

logger = logging.getLogger(__name__)

class SiteWideAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting sitewide analysis for audit {self.audit_id}")
        
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        total_pages = len(pages)
        depth_distribution = {}
        pages_too_deep = 0
        total_load_time = 0
        pages_with_load_time = 0
        status_distribution = {}
        content_type_distribution = {}
        thin_indexable_pages = 0
        indexable_count = 0
        non_indexable_count = 0

        for page in pages:
            depth = page.get('crawl_depth')
            if depth is not None:
                depth_distribution[depth] = depth_distribution.get(depth, 0) + 1
                if depth > 3:
                    pages_too_deep += 1

            rt = page.get('response_time_ms') or page.get('response_time')
            if rt:
                total_load_time += rt
                pages_with_load_time += 1

            status = page.get('status_code')
            if status:
                status_group = f"{str(status)[0]}xx"
                status_distribution[status_group] = status_distribution.get(status_group, 0) + 1

            content_type = page.get('content_type')
            if content_type:
                base_type = content_type.split(';')[0]
                content_type_distribution[base_type] = content_type_distribution.get(base_type, 0) + 1

            is_indexable = page.get('is_indexable', True)
            if is_indexable:
                indexable_count += 1
            else:
                non_indexable_count += 1

            word_count = page.get('word_count')
            if is_indexable and word_count is not None and word_count < 50:
                thin_indexable_pages += 1
                await self._add_issue(page.get('id'), page.get('url'), 'warning', 'thin_content', "Indexable page with very low word count (< 50 words)", "Add more substantial content to this page.", word_count)

        # Site architecture
        await self._add_issue(None, None, 'info', 'depth_distribution', "Site architecture depth distribution", "Review the distribution of page depths.", depth_distribution)
        
        if pages_too_deep > 0:
            await self._add_issue(None, None, 'warning', 'pages_too_deep', f"{pages_too_deep} pages are deeper than 3 clicks from homepage", "Improve internal linking to bring pages closer to homepage.", pages_too_deep)

        if pages_with_load_time > 0:
            avg_load_time = total_load_time / pages_with_load_time
            await self._add_issue(None, None, 'info', 'avg_page_load_time', f"Average page load time: {avg_load_time:.0f}ms", "General performance metric.", avg_load_time)

        await self._add_issue(None, None, 'info', 'status_distribution', "HTTP status distribution", "Monitor HTTP status codes.", status_distribution)
        await self._add_issue(None, None, 'info', 'content_type_distribution', "Content type distribution", "Review types of content being crawled.", content_type_distribution)
        
        await self._add_issue(None, None, 'info', 'indexable_counts', f"Total Indexable: {indexable_count}, Non-indexable: {non_indexable_count}", "Ensure correct pages are indexable.", {'indexable': indexable_count, 'non_indexable': non_indexable_count})

        # Social media links
        links = await self.db.get_links(self.audit_id, is_internal=False)
        social_platforms = ['facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com', 'youtube.com']
        has_social_links = False
        for link in links:
            target = link.get('target_url')
            if target:
                domain = urllib.parse.urlparse(target).netloc.lower()
                if any(p in domain for p in social_platforms):
                    has_social_links = True
                    break
        
        if not has_social_links:
            await self._add_issue(None, None, 'info', 'no_social_links', "No social media links found on the site", "Consider adding links to your social profiles.", None)

        # 404 page check
        homepage = next((p for p in pages if p.get('crawl_depth') == 0), None)
        if homepage:
            base_url = homepage.get('url')
            if base_url:
                parsed = urllib.parse.urlparse(base_url)
                test_url = f"{parsed.scheme}://{parsed.netloc}/404-page-not-found-test-{int(time.time())}"
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(test_url)
                        if resp.status_code == 404:
                            text = resp.text
                            if 'nginx' in text.lower() or 'apache' in text.lower() or len(text) < 500:
                                await self._add_issue(None, None, 'info', 'default_404', "Site appears to use a default server 404 page", "Create a custom 404 page to retain users.", test_url)
                            else:
                                await self._add_issue(None, None, 'info', 'custom_404', "Site has a custom 404 page", "Good practice.", None)
                except Exception as e:
                    logger.error(f"Error checking 404 page for {test_url}: {e}")

        # Summary and Health Score
        issues = await self.db.get_issues(self.audit_id)
        severity_counts = {'critical': 0, 'warning': 0, 'info': 0}
        
        for issue in issues:
            sev = issue.get('severity')
            if sev in severity_counts:
                severity_counts[sev] += 1
                
        await self._add_issue(None, None, 'info', 'issues_summary', "Total pages with issues by severity", "Issue summary.", severity_counts)

        if total_pages > 0:
            score = 100 - (severity_counts['critical'] * 3 + severity_counts['warning'] * 1 + severity_counts['info'] * 0.2) / total_pages
            score = max(0, min(100, score))
            await self.db.update_audit(self.audit_id, health_score=score, total_issues=len(issues))

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='sitewide',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
