"""
Crawl Scheduler and Regression Alerting Engine for Vaprolls SEO Spider.
Automates recurring crawls and compares results against previous baselines to alert on regressions.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from config import get_config, Config
from database.db import Database
from crawler.engine import CrawlEngine
from reports.comparator import AuditComparator

# Analyzers for pipeline execution
from analyzers.technical import TechnicalAnalyzer
from analyzers.onpage import OnPageAnalyzer
from analyzers.links import LinkAnalyzer

try:
    from analyzers.images import ImageAnalyzer
except ImportError:
    ImageAnalyzer = None
try:
    from analyzers.performance import PerformanceAnalyzer
except ImportError:
    PerformanceAnalyzer = None
try:
    from analyzers.security import SecurityAnalyzer
except ImportError:
    SecurityAnalyzer = None
try:
    from analyzers.security_headers import SecurityHeadersAnalyzer
except ImportError:
    SecurityHeadersAnalyzer = None
try:
    from analyzers.sitemap_auditor import SitemapAuditor
except ImportError:
    SitemapAuditor = None
try:
    from analyzers.robots_auditor import RobotsAuditor
except ImportError:
    RobotsAuditor = None
try:
    from analyzers.social_meta import SocialMetaAnalyzer
except ImportError:
    SocialMetaAnalyzer = None
try:
    from analyzers.pagination_auditor import PaginationAuditor
except ImportError:
    PaginationAuditor = None

logger = logging.getLogger(__name__)

class CrawlScheduler:
    """
    Automates scheduled crawl execution and regression detection:
    - Finds prior audits for the domain to use as baseline
    - Runs a fresh audit with full analyzer pipeline
    - Auto-compares new audit with previous baseline
    - Flags regressions: new 4xx/5xx errors, dropped pages, health score drops, lost canonicals
    """
    def __init__(self, db: Database):
        self.db = db

    async def find_previous_audit_id(self, domain: str) -> Optional[str]:
        """Finds the most recent completed audit for this domain."""
        audits = await self.db.list_audits()
        for a in audits:
            if a.get('domain', '').lower() == domain.lower() and a.get('status') in ('completed', 'done', 'analyzing'):
                return a['id']
        return None

    async def run_and_compare(self, url: str, config: Optional[Config] = None) -> Dict[str, Any]:
        """Runs a complete crawl and auto-compares against the latest baseline audit for regressions."""
        if config is None:
            config = get_config()

        parsed = urlparse(url)
        domain = parsed.netloc

        # 1. Look for previous audit baseline
        baseline_id = await self.find_previous_audit_id(domain)
        if baseline_id:
            logger.info(f"Found existing baseline audit {baseline_id} for domain {domain}")
        else:
            logger.info(f"No previous baseline found for domain {domain}. This will be the baseline.")

        # 2. Run fresh crawl
        engine = CrawlEngine(start_url=url, config=config, database=self.db)
        new_audit_id = await engine.crawl()

        # 3. Run analyzer suite
        analyzers = [
            TechnicalAnalyzer(self.db, new_audit_id),
            OnPageAnalyzer(self.db, new_audit_id),
            LinkAnalyzer(self.db, new_audit_id),
        ]
        if ImageAnalyzer: analyzers.append(ImageAnalyzer(self.db, new_audit_id))
        if PerformanceAnalyzer: analyzers.append(PerformanceAnalyzer(self.db, new_audit_id))
        if SecurityAnalyzer: analyzers.append(SecurityAnalyzer(self.db, new_audit_id))
        if SecurityHeadersAnalyzer: analyzers.append(SecurityHeadersAnalyzer(self.db, new_audit_id))
        if SitemapAuditor: analyzers.append(SitemapAuditor(self.db, new_audit_id))
        if RobotsAuditor: analyzers.append(RobotsAuditor(self.db, new_audit_id))
        if SocialMetaAnalyzer: analyzers.append(SocialMetaAnalyzer(self.db, new_audit_id))
        if PaginationAuditor: analyzers.append(PaginationAuditor(self.db, new_audit_id))

        for an in analyzers:
            try:
                await an.analyze()
            except Exception as e:
                logger.error(f"Analyzer {an.__class__.__name__} failed during scheduled run: {e}")

        # Update audit health score
        summary = await self.db.get_audit_summary(new_audit_id)
        issues = summary.get('issues_by_severity', {})
        score = max(0.0, 100.0 - (issues.get('critical', 0) * 2.0) - (issues.get('warning', 0) * 0.5))
        await self.db.update_audit(new_audit_id, health_score=score, status='completed')

        # 4. Compare with baseline if available
        comparison_res = None
        regression_alert = None

        if baseline_id and AuditComparator:
            try:
                comparator = AuditComparator(self.db, baseline_id, new_audit_id)
                comparison_res = await comparator.compare()
                regression_alert = self.generate_regression_alert(comparison_res)
            except Exception as e:
                logger.error(f"Audit comparison failed: {e}")

        return {
            'domain': domain,
            'audit_id': new_audit_id,
            'baseline_id': baseline_id,
            'health_score': score,
            'comparison': comparison_res,
            'regression_alert': regression_alert
        }

    def generate_regression_alert(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes comparison output to detect and alert on SEO regressions."""
        summary = comparison.get('summary', {})
        regressions: List[str] = []

        # 1. Health score drop
        score_diff = summary.get('health_score_diff', 0.0) or 0.0
        if score_diff < -5.0:
            regressions.append(f"CRITICAL: Health score dropped by {abs(score_diff):.1f} points ({summary.get('baseline_health_score')} -> {summary.get('current_health_score')})")

        # 2. Pages returning new errors
        status_changes = comparison.get('status_changes', [])
        new_errors = [sc for sc in status_changes if sc.get('new', 0) >= 400 and sc.get('old', 0) < 400]
        if new_errors:
            regressions.append(f"CRITICAL: {len(new_errors)} pages that were working now return 4xx/5xx HTTP errors")

        # 3. Pages dropped from crawl
        removed_count = summary.get('removed_count', 0)
        if removed_count > 0:
            regressions.append(f"WARNING: {removed_count} URLs present in baseline were missing from the latest crawl")

        # 4. Indexability shifts
        idx_changes = comparison.get('indexability_changes', [])
        lost_indexable = [ic for ic in idx_changes if ic.get('old') is True and ic.get('new') is False]
        if lost_indexable:
            regressions.append(f"WARNING: {len(lost_indexable)} previously indexable pages have become non-indexable (noindex or blocked)")

        has_regression = len(regressions) > 0
        status = 'FAIL' if any('CRITICAL' in r for r in regressions) else ('WARN' if has_regression else 'PASS')

        return {
            'status': status,
            'has_regression': has_regression,
            'regressions_count': len(regressions),
            'regressions': regressions,
            'timestamp': datetime.utcnow().isoformat()
        }
