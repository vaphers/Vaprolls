import argparse
import asyncio
import os
import sys
import time
from typing import Dict, Any

from config import get_config
from database.db import Database
from crawler.engine import CrawlEngine
from analyzers.technical import TechnicalAnalyzer
from analyzers.onpage import OnPageAnalyzer
from analyzers.links import LinkAnalyzer

# Try importing other analyzers
try:
    from analyzers.images import ImageAnalyzer
except ImportError:
    ImageAnalyzer = None
try:
    from analyzers.performance import PerformanceAnalyzer
except ImportError:
    PerformanceAnalyzer = None
try:
    from analyzers.mobile import MobileAnalyzer
except ImportError:
    MobileAnalyzer = None
try:
    from analyzers.structured_data import StructuredDataAnalyzer
except ImportError:
    StructuredDataAnalyzer = None
try:
    from analyzers.security import SecurityAnalyzer
except ImportError:
    SecurityAnalyzer = None
try:
    from analyzers.keywords import KeywordAnalyzer
except ImportError:
    KeywordAnalyzer = None
try:
    from analyzers.sitewide import SiteWideAnalyzer
except ImportError:
    SiteWideAnalyzer = None

try:
    from analyzers.pagerank import PageRankAnalyzer
except ImportError:
    PageRankAnalyzer = None

try:
    from analyzers.hreflang import HreflangAnalyzer
except ImportError:
    HreflangAnalyzer = None

try:
    from analyzers.js_seo import JsSeoAnalyzer
except ImportError:
    JsSeoAnalyzer = None

try:
    from analyzers.custom_search import CustomSearchAnalyzer
except ImportError:
    CustomSearchAnalyzer = None

try:
    from analyzers.content import ContentAnalyzer
except ImportError:
    ContentAnalyzer = None

try:
    from analyzers.accessibility import AccessibilityAnalyzer
except ImportError:
    AccessibilityAnalyzer = None

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

try:
    from analyzers.log_analyzer import LogFileAnalyzer
except ImportError:
    LogFileAnalyzer = None

try:
    from reports.comparator import AuditComparator
except ImportError:
    AuditComparator = None

try:
    from services.gsc_client import GSCClient
except ImportError:
    GSCClient = None

try:
    from services.crux_client import CruxClient
except ImportError:
    CruxClient = None

try:
    from reports.generator import ReportGenerator
except ImportError:
    ReportGenerator = None

try:
    from ai.gemini_enhancer import GeminiEnhancer
except ImportError:
    GeminiEnhancer = None


async def run_audit(args):
    config = get_config()
    # Override config with args
    if args.max_pages:
        config.MAX_PAGES = args.max_pages
    if args.concurrency:
        config.CRAWL_CONCURRENCY = args.concurrency
    if args.delay is not None:
        config.CRAWL_DELAY = args.delay
    if args.no_js:
        config.JS_RENDER_ENABLED = False
    if getattr(args, 'crawl_subdomains', False):
        config.CRAWL_SUBDOMAINS = True
    if getattr(args, 'allowed_domains', None):
        config.ALLOWED_DOMAINS = args.allowed_domains
    if getattr(args, 'max_depth', None):
        config.MAX_CRAWL_DEPTH = args.max_depth
    if getattr(args, 'psi_key', None):
        config.PSI_API_KEY = args.psi_key
        
    # Enterprise Crawl Mode & Scope
    if getattr(args, 'mode', None):
        config.CRAWL_MODE = args.mode
    if getattr(args, 'urls_file', None) and os.path.exists(args.urls_file):
        with open(args.urls_file, 'r', encoding='utf-8') as f:
            config.URLS_LIST = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(config.URLS_LIST)} URLs from {args.urls_file}")
    if getattr(args, 'include', None):
        config.INCLUDE_REGEX = args.include
    if getattr(args, 'exclude', None):
        config.EXCLUDE_REGEX = args.exclude
    if getattr(args, 'user_agent_preset', None):
        config.USER_AGENT_PRESET = args.user_agent_preset
    if getattr(args, 'basic_auth', None):
        if ':' in args.basic_auth:
            u, p = args.basic_auth.split(':', 1)
            config.HTTP_AUTH = {'username': u, 'password': p}
    if getattr(args, 'proxy', None):
        config.PROXY = args.proxy
    
    url = args.url
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    
    os.makedirs(args.output, exist_ok=True)
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    
    print(f"Starting audit for {url} [Mode: {config.CRAWL_MODE.upper()}, Bot: {config.USER_AGENT_PRESET}]...")
    start_time = time.time()
    
    async with Database(config.DB_PATH) as db:
        def progress_callback(data):
            crawled = data.get("crawled", 0)
            total = data.get("total", 0)
            current_url = data.get("url", "")
            sys.stdout.write(f"\r[{crawled}/{total}] Crawling: {current_url[:60]:<60}")
            sys.stdout.flush()
            
        engine = CrawlEngine(start_url=url, config=config, database=db, progress_callback=progress_callback)
        audit_id = await engine.crawl()
        
        print("\n\nCrawling completed. Running analyzers...")
        
        analyzers = [
            TechnicalAnalyzer(db, audit_id),
            OnPageAnalyzer(db, audit_id),
            LinkAnalyzer(db, audit_id),
        ]
        
        if ImageAnalyzer: analyzers.append(ImageAnalyzer(db, audit_id))
        if PerformanceAnalyzer: analyzers.append(PerformanceAnalyzer(db, audit_id))
        if MobileAnalyzer: analyzers.append(MobileAnalyzer(db, audit_id))
        if StructuredDataAnalyzer: analyzers.append(StructuredDataAnalyzer(db, audit_id))
        if SecurityAnalyzer: analyzers.append(SecurityAnalyzer(db, audit_id))
        if KeywordAnalyzer: analyzers.append(KeywordAnalyzer(db, audit_id))
        if SiteWideAnalyzer: analyzers.append(SiteWideAnalyzer(db, audit_id))
        
        # Enterprise Analyzers
        if PageRankAnalyzer: analyzers.append(PageRankAnalyzer(db, audit_id))
        if HreflangAnalyzer: analyzers.append(HreflangAnalyzer(db, audit_id))
        if JsSeoAnalyzer: analyzers.append(JsSeoAnalyzer(db, audit_id))
        if CustomSearchAnalyzer: analyzers.append(CustomSearchAnalyzer(db, audit_id))
        if ContentAnalyzer: analyzers.append(ContentAnalyzer(db, audit_id))
        if AccessibilityAnalyzer: analyzers.append(AccessibilityAnalyzer(db, audit_id))
        if SecurityHeadersAnalyzer: analyzers.append(SecurityHeadersAnalyzer(db, audit_id))
        if SitemapAuditor: analyzers.append(SitemapAuditor(db, audit_id))
        if RobotsAuditor: analyzers.append(RobotsAuditor(db, audit_id))
        if SocialMetaAnalyzer: analyzers.append(SocialMetaAnalyzer(db, audit_id))
        if PaginationAuditor: analyzers.append(PaginationAuditor(db, audit_id))
        
        for analyzer in analyzers:
            analyzer_name = analyzer.__class__.__name__
            print(f"Running {analyzer_name}...")
            await analyzer.analyze()

        # Optional Log File Analysis
        if getattr(args, 'log_file', None) and LogFileAnalyzer and os.path.exists(args.log_file):
            print(f"\nIngesting server access logs: {args.log_file}...")
            log_an = LogFileAnalyzer(db, audit_id, args.log_file)
            log_res = await log_an.ingest_and_analyze()
            print(f"  Processed {log_res.get('total_bot_hits', 0)} bot hits from log file.")

        # Optional GSC Data Overlay
        if getattr(args, 'gsc_token', None) and GSCClient:
            print("\nPulling Google Search Console performance data...")
            gsc = GSCClient(db, audit_id, args.gsc_token)
            gsc_res = await gsc.fetch_and_store_performance(url)
            print(f"  GSC rows pulled: {gsc_res.get('rows_ingested', 0)}")
            
        # Optional PageSpeed Insights / CrUX CWV
        if getattr(args, 'psi_key', None) and CruxClient:
            print("\nPulling Google PageSpeed Insights & Core Web Vitals...")
            crux = CruxClient(db, audit_id, api_key=args.psi_key)
            pages = await db.get_pages(audit_id)
            sample_urls = [p['url'] for p in pages if p.get('crawl_depth') == 0]
            sample_urls += [p['url'] for p in sorted(pages, key=lambda x: x.get('unique_inlinks', 0), reverse=True)[:9]]
            sample_urls = list(dict.fromkeys(sample_urls))[:10]
            if sample_urls:
                print(f"  Fetching PSI metrics for {len(sample_urls)} priority URLs...")
                psi_results = await crux.batch_fetch_metrics(sample_urls)
                print(f"  PSI metrics successfully captured for {len(psi_results)} URLs.")

        # Summary
        summary = await db.get_audit_summary(audit_id)
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*40)
        print("AUDIT SUMMARY")
        print("="*40)
        print(f"Total pages crawled: {summary.get('total_pages', 0)}")
        
        issues = summary.get('issues_by_severity', {})
        print("Issues by Severity:")
        print(f"  Critical: {issues.get('critical', 0)}")
        print(f"  Warning:  {issues.get('warning', 0)}")
        print(f"  Info:     {issues.get('info', 0)}")
        
        health_score = 100
        health_score -= issues.get('critical', 0) * 2
        health_score -= issues.get('warning', 0) * 0.5
        health_score = max(0, health_score)
        
        print(f"\nHealth Score: {health_score:.1f}/100")
        print(f"Time taken: {elapsed:.2f} seconds")
        print("="*40)
        
        # Save health score to audit
        await db.update_audit(audit_id, health_score=health_score)
        
        # AI Enhancement (optional)
        if GeminiEnhancer:
            print("\nRunning AI enhancement (if API key is set)...")
            enhancer = GeminiEnhancer(db, audit_id)
            if enhancer.enabled:
                await enhancer.enhance()
                print("AI enhancement completed.")
            else:
                print("Gemini API key not set. Skipping AI enhancement.")
        
        # Generate Reports
        if ReportGenerator:
            print(f"\nGenerating reports in '{args.output}'...")
            report_gen = ReportGenerator(db, audit_id, args.output)
            
            try:
                if args.format in ('html', 'all'):
                    html_path = await report_gen.generate_html()
                    print(f"  HTML report: {html_path}")
                if args.format in ('csv', 'all'):
                    csv_path = await report_gen.generate_csv()
                    print(f"  CSV files:   {csv_path}")
                if args.format in ('docx', 'all'):
                    docx_path = await report_gen.generate_docx()
                    print(f"  Word doc:    {docx_path}")
                
                # Always generate Excel
                if args.format == 'all':
                    excel_path = await report_gen.generate_excel()
                    print(f"  Excel file:  {excel_path}")
                    
                print("\nReports generated successfully!")
            except Exception as e:
                print(f"\nError generating reports: {e}")
                print("You can regenerate reports later with: python cli.py report " + audit_id)
        else:
            print("\nReport generator not available. Install python-docx and openpyxl.")


async def run_list():
    config = get_config()
    db_path = config.DB_PATH
    if not os.path.exists(db_path):
        print("No database found. Run an audit first.")
        return
        
    async with Database(db_path) as db:
        audits = await db.list_audits()
        if not audits:
            print("No audits found.")
            return
            
        print(f"{'ID':<38} | {'Domain':<25} | {'Date':<20} | {'Pages':<6} | {'Health Score'}")
        print("-" * 110)
        for audit in audits:
            date_str = audit.get('started_at', '')[:19].replace('T', ' ')
            score = audit.get('health_score')
            score_str = f"{score:.1f}" if score is not None else "N/A"
            print(f"{audit['id']:<38} | {audit['domain']:<25} | {date_str:<20} | {audit.get('total_pages', 0):<6} | {score_str}")


async def run_report(args):
    if not ReportGenerator:
        print("Report generator not available. Install python-docx and openpyxl.")
        return
    
    config = get_config()
    db_path = config.DB_PATH
    if not os.path.exists(db_path):
        print("No database found. Run an audit first.")
        return
    
    async with Database(db_path) as db:
        audit = await db.get_audit(args.audit_id)
        if not audit:
            print(f"Audit {args.audit_id} not found.")
            return
        
        output_dir = getattr(args, 'output', 'reports_output')
        report_gen = ReportGenerator(db, args.audit_id, output_dir)
        
        print(f"Generating {args.format} report for audit {args.audit_id}...")
        try:
            if args.format == 'all':
                paths = await report_gen.generate_all()
                for fmt, path in paths.items():
                    print(f"  {fmt}: {path}")
            elif args.format == 'html':
                path = await report_gen.generate_html()
                print(f"  HTML report: {path}")
            elif args.format == 'csv':
                path = await report_gen.generate_csv()
                print(f"  CSV files: {path}")
            elif args.format == 'docx':
                path = await report_gen.generate_docx()
                print(f"  Word doc: {path}")
            print("\nReports generated successfully!")
        except Exception as e:
            print(f"Error generating report: {e}")


async def run_compare(args):
    if not AuditComparator:
        print("AuditComparator module not available.")
        return
    config = get_config()
    db_path = config.DB_PATH
    if not os.path.exists(db_path):
        print("No database found.")
        return

    async with Database(db_path) as db:
        try:
            comp = AuditComparator(db, args.baseline_id, args.current_id)
            res = await comp.compare()
            print("\n" + "="*60)
            print("AUDIT MIGRATION / COMPARISON REPORT")
            print("="*60)
            s = res['summary']
            print(f"Baseline Pages: {s['baseline_pages']} | Current Pages: {s['current_pages']} (Diff: {s['pages_diff']:+d})")
            b_score = s.get('baseline_health_score')
            c_score = s.get('current_health_score')
            b_str = f"{b_score:.1f}" if b_score is not None else "N/A"
            c_str = f"{c_score:.1f}" if c_score is not None else "N/A"
            d_score = s.get('health_score_diff')
            d_str = f"{d_score:+.1f}" if d_score is not None else "N/A"
            print(f"Health Score: {b_str} -> {c_str} ({d_str})")
            print(f"New URLs: {s['added_count']} | Removed URLs: {s['removed_count']}")
            print(f"Status Code Changes: {s['status_changes_count']}")
            print(f"Title Changes: {s['title_changes_count']} | Canonical Changes: {s['canonical_changes_count']}")
            print(f"Indexability Shifts: {s['indexability_changes_count']}")
            if res['status_changes']:
                print("\nStatus Code Changes:")
                for sc in res['status_changes'][:15]:
                    print(f"  {sc['url'][:70]} : {sc['old']} -> {sc['new']}")
            if res['indexability_changes']:
                print("\nIndexability Regressions:")
                for ic in res['indexability_changes'][:10]:
                    print(f"  {ic['url'][:70]} : Indexable={ic['old']} -> Indexable={ic['new']}")
            print("="*60)
        except Exception as e:
            print(f"Comparison error: {e}")


async def run_schedule(args):
    from scheduler import CrawlScheduler
    config = get_config()
    if args.max_pages:
        config.MAX_PAGES = args.max_pages

    db_path = config.DB_PATH
    async with Database(db_path) as db:
        scheduler = CrawlScheduler(db)
        print(f"\nStarting scheduled run for {args.url} (Frequency: {args.every})...")
        res = await scheduler.run_and_compare(args.url, config)
        print(f"\nCompleted run for {res['domain']} (Audit ID: {res['audit_id']})")
        print(f"Health Score: {res['health_score']:.1f}/100")

        alert = res.get('regression_alert')
        if alert:
            print("\n" + "="*50)
            print(f"REGRESSION AUDIT STATUS: [{alert['status']}]")
            print("="*50)
            if alert['has_regression']:
                for reg in alert['regressions']:
                    print(f"  * {reg}")
            else:
                print("  [OK] No SEO regressions detected compared to baseline!")
            print("="*50)
        else:
            print("\nBaseline created. Future scheduled runs will compare regressions against this baseline.")


def main_cli(args=None):
    parser = argparse.ArgumentParser(description="SEO Auditor CLI")
    parser.add_argument('--verbose', action='store_true', help="Enable debug logging")
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Run a new SEO audit')
    audit_parser.add_argument('url', help='The URL to audit')
    audit_parser.add_argument('--max-pages', type=int, help='Maximum number of pages to crawl')
    audit_parser.add_argument('--concurrency', type=int, help='Concurrent requests')
    audit_parser.add_argument('--delay', type=float, help='Delay between requests in seconds')
    audit_parser.add_argument('--no-js', action='store_true', help='Disable JavaScript rendering')
    audit_parser.add_argument('--output', default='reports_output/', help='Output directory for reports')
    audit_parser.add_argument('--format', choices=['html', 'csv', 'docx', 'all'], default='all', help='Report format')
    
    # Enterprise Crawl Controls
    audit_parser.add_argument('--mode', choices=['spider', 'list', 'sitemap'], default='spider', help='Crawl mode')
    audit_parser.add_argument('--urls-file', help='Path to file containing URLs (for list mode)')
    audit_parser.add_argument('--include', action='append', help='Regex pattern to include in crawl scope')
    audit_parser.add_argument('--exclude', action='append', help='Regex pattern to exclude from crawl scope')
    audit_parser.add_argument('--user-agent-preset', choices=['default', 'googlebot_smartphone', 'googlebot_desktop', 'bingbot', 'chrome_desktop'], default='default', help='Bot / User-Agent preset')
    audit_parser.add_argument('--basic-auth', help='HTTP basic auth credentials (user:password)')
    audit_parser.add_argument('--proxy', help='HTTP/SOCKS5 proxy address')
    audit_parser.add_argument('--log-file', help='Path to server access log file to analyze')
    audit_parser.add_argument('--gsc-token', help='Google Search Console OAuth token for organic metrics')
    audit_parser.add_argument('--psi-key', help='Google PageSpeed Insights API key for Core Web Vitals')
    audit_parser.add_argument('--crawl-subdomains', action='store_true', help='Include subdomains in crawl scope')
    audit_parser.add_argument('--allowed-domains', action='append', help='Additional domains to include in crawl scope')
    audit_parser.add_argument('--max-depth', type=int, help='Maximum crawl depth')
    
    # List command
    subparsers.add_parser('list', help='List previous audits')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate a report for a previous audit')
    report_parser.add_argument('audit_id', help='The ID of the audit')
    report_parser.add_argument('--format', choices=['html', 'csv', 'docx', 'all'], default='all', help='Report format')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two audits (migration/staging diffing)')
    compare_parser.add_argument('baseline_id', help='Baseline / Pre-migration audit ID')
    compare_parser.add_argument('current_id', help='Current / Post-migration audit ID')

    # Schedule command
    schedule_parser = subparsers.add_parser('schedule', help='Run automated crawl with regression detection')
    schedule_parser.add_argument('url', help='The URL to audit')
    schedule_parser.add_argument('--every', choices=['daily', 'weekly', 'monthly', 'once'], default='once', help='Crawl schedule frequency')
    schedule_parser.add_argument('--max-pages', type=int, help='Maximum number of pages to crawl')
    
    parsed_args = parser.parse_args(args)
    
    if parsed_args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    else:
        import logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        
    try:
        if parsed_args.command == 'audit':
            asyncio.run(run_audit(parsed_args))
        elif parsed_args.command == 'list':
            asyncio.run(run_list())
        elif parsed_args.command == 'report':
            asyncio.run(run_report(parsed_args))
        elif parsed_args.command == 'compare':
            asyncio.run(run_compare(parsed_args))
        elif parsed_args.command == 'schedule':
            asyncio.run(run_schedule(parsed_args))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)


if __name__ == '__main__':
    main_cli()
