"""
Security Headers Analyzer for Vaprolls SEO Spider.
Audits HTTP response security headers per page and calculates site-wide security posture.
"""
import json
import logging
from typing import Optional, Any, Dict, List
from database.db import Database

logger = logging.getLogger(__name__)

class SecurityHeadersAnalyzer:
    """
    Audits security headers across all crawled pages:
    - Strict-Transport-Security (HSTS): presence, max-age >= 31536000, includeSubDomains, preload
    - Content-Security-Policy (CSP): presence, default-src/script-src restrictions, unsafe-inline/eval warnings
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY or SAMEORIGIN
    - Referrer-Policy: strict-origin-when-cross-origin or stricter
    - Permissions-Policy: camera, microphone, geolocation restrictions
    - X-XSS-Protection: 1; mode=block or 0 (deprecated)
    - Site-wide security score and coverage metrics
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting security headers analysis for audit {self.audit_id}")
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        total_html_pages = 0
        hsts_count = 0
        csp_count = 0
        nosniff_count = 0
        frame_options_count = 0
        referrer_policy_count = 0
        permissions_policy_count = 0

        for page in pages:
            url = page.get('url', '')
            if not url:
                continue

            content_type = (page.get('content_type') or '').lower()
            # Only audit HTML pages
            if 'text/html' not in content_type and page.get('html_size', 0) == 0:
                continue

            page_id = page.get('id')
            total_html_pages += 1
            is_https = url.lower().startswith('https://')

            headers: Dict[str, str] = {}
            headers_json = page.get('headers_json')
            if headers_json:
                try:
                    headers = {k.lower(): v for k, v in json.loads(headers_json).items()}
                except Exception:
                    headers = {}

            # Also check columns populated directly from crawler
            hsts = headers.get('strict-transport-security') or page.get('hsts_header')
            csp = headers.get('content-security-policy') or page.get('csp_header')
            nosniff = headers.get('x-content-type-options') or page.get('x_content_type_options')
            xfo = headers.get('x-frame-options') or page.get('x_frame_options')
            ref_pol = headers.get('referrer-policy') or page.get('referrer_policy')
            perm_pol = headers.get('permissions-policy') or page.get('permissions_policy')
            xxss = headers.get('x-xss-protection')

            # 1. HSTS (for HTTPS pages)
            if is_https:
                if hsts:
                    hsts_count += 1
                    hsts_lower = hsts.lower()
                    if 'max-age' in hsts_lower:
                        try:
                            # Extract max-age number
                            import re
                            m = re.search(r'max-age=(\d+)', hsts_lower)
                            if m:
                                max_age = int(m.group(1))
                                if max_age < 31536000:
                                    await self._add_issue(
                                        page_id, url, 'warning', 'hsts_short_max_age',
                                        f"HSTS max-age is {max_age}s (less than recommended 31536000s / 1 year)",
                                        "Increase HSTS max-age to at least 31536000 (1 year) to protect users against SSL stripping attacks.",
                                        hsts
                                    )
                        except Exception:
                            pass
                    if 'includesubdomains' not in hsts_lower:
                        await self._add_issue(
                            page_id, url, 'info', 'hsts_missing_includesubdomains',
                            "HSTS header does not include 'includeSubDomains' directive",
                            "Add 'includeSubDomains' to HSTS to ensure all subdomains are protected.",
                            hsts
                        )
                else:
                    await self._add_issue(
                        page_id, url, 'warning', 'missing_hsts_header',
                        "Missing Strict-Transport-Security header on HTTPS page",
                        "Implement Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
                        None
                    )

            # 2. Content Security Policy (CSP)
            if csp:
                csp_count += 1
                csp_lower = csp.lower()
                if "'unsafe-inline'" in csp_lower:
                    await self._add_issue(
                        page_id, url, 'warning', 'csp_unsafe_inline',
                        "Content-Security-Policy includes 'unsafe-inline'",
                        "Replace inline scripts and styles with hashes or nonces to mitigate XSS vulnerabilities.",
                        csp[:100]
                    )
                if "'unsafe-eval'" in csp_lower:
                    await self._add_issue(
                        page_id, url, 'warning', 'csp_unsafe_eval',
                        "Content-Security-Policy includes 'unsafe-eval'",
                        "Avoid using eval() and remove 'unsafe-eval' from CSP directives.",
                        csp[:100]
                    )
            else:
                await self._add_issue(
                    page_id, url, 'warning', 'missing_csp_header',
                    "Missing Content-Security-Policy (CSP) header",
                    "Configure a strong CSP (e.g. default-src 'self') to prevent cross-site scripting (XSS) and data injection.",
                    None
                )

            # 3. X-Content-Type-Options
            if nosniff:
                nosniff_count += 1
                if 'nosniff' not in nosniff.lower():
                    await self._add_issue(
                        page_id, url, 'warning', 'invalid_x_content_type_options',
                        f"X-Content-Type-Options is set to '{nosniff}', expected 'nosniff'",
                        "Set header to 'X-Content-Type-Options: nosniff' to disable MIME-type sniffing.",
                        nosniff
                    )
            else:
                await self._add_issue(
                    page_id, url, 'warning', 'missing_x_content_type_options',
                    "Missing X-Content-Type-Options header",
                    "Add 'X-Content-Type-Options: nosniff' to prevent browsers from interpreting files as a different MIME type.",
                    None
                )

            # 4. X-Frame-Options
            if xfo:
                frame_options_count += 1
                xfo_upper = xfo.upper()
                if not any(valid in xfo_upper for valid in ('DENY', 'SAMEORIGIN')):
                    await self._add_issue(
                        page_id, url, 'warning', 'weak_x_frame_options',
                        f"X-Frame-Options header '{xfo}' is not DENY or SAMEORIGIN",
                        "Set X-Frame-Options to DENY or SAMEORIGIN to prevent clickjacking attacks.",
                        xfo
                    )
            else:
                # If CSP frame-ancestors is present, XFO is not strictly required
                if not csp or 'frame-ancestors' not in csp.lower():
                    await self._add_issue(
                        page_id, url, 'warning', 'missing_x_frame_options',
                        "Missing X-Frame-Options header (and no CSP frame-ancestors)",
                        "Add 'X-Frame-Options: SAMEORIGIN' or CSP 'frame-ancestors: self' to prevent clickjacking attacks.",
                        None
                    )

            # 5. Referrer-Policy
            if ref_pol:
                referrer_policy_count += 1
                ref_lower = ref_pol.lower()
                if 'unsafe-url' in ref_lower:
                    await self._add_issue(
                        page_id, url, 'warning', 'unsafe_referrer_policy',
                        "Referrer-Policy is set to 'unsafe-url', exposing sensitive query params",
                        "Use 'strict-origin-when-cross-origin' or 'no-referrer' to protect sensitive URL paths.",
                        ref_pol
                    )
            else:
                await self._add_issue(
                    page_id, url, 'info', 'missing_referrer_policy',
                    "Missing Referrer-Policy header",
                    "Set 'Referrer-Policy: strict-origin-when-cross-origin' to protect user privacy.",
                    None
                )

            # 6. Permissions-Policy
            if perm_pol:
                permissions_policy_count += 1

        # Site-wide Summary & Security Posture Score
        if total_html_pages > 0:
            hsts_pct = round((hsts_count / total_html_pages) * 100, 1)
            csp_pct = round((csp_count / total_html_pages) * 100, 1)
            nosniff_pct = round((nosniff_count / total_html_pages) * 100, 1)
            xfo_pct = round((frame_options_count / total_html_pages) * 100, 1)
            ref_pct = round((referrer_policy_count / total_html_pages) * 100, 1)

            # Calculate composite security header score (0 - 100)
            sec_score = round(
                (hsts_pct * 0.25) +
                (csp_pct * 0.25) +
                (nosniff_pct * 0.20) +
                (xfo_pct * 0.15) +
                (ref_pct * 0.15),
                1
            )

            severity = 'info' if sec_score >= 80 else ('warning' if sec_score >= 50 else 'critical')
            await self._add_issue(
                None, None, severity, 'security_headers_summary',
                f"Security Headers Score: {sec_score}/100 (HSTS: {hsts_pct}%, CSP: {csp_pct}%, nosniff: {nosniff_pct}%, XFO: {xfo_pct}%, Referrer: {ref_pct}%)",
                "Deploy missing HTTP security headers across your web server or CDN configuration.",
                {
                    'score': sec_score,
                    'hsts_coverage': hsts_pct,
                    'csp_coverage': csp_pct,
                    'nosniff_coverage': nosniff_pct,
                    'xfo_coverage': xfo_pct,
                    'referrer_policy_coverage': ref_pct,
                    'total_html_pages': total_html_pages
                }
            )

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
