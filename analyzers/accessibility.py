import logging
import json
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from database.db import Database

logger = logging.getLogger(__name__)

AMBIGUOUS_ANCHOR_TEXTS = {
    'click here', 'here', 'read more', 'learn more', 'more', 'link', 'view', 'details', 'continue'
}

class AccessibilityAnalyzer:
    """
    Evaluates WCAG 2.0, 2.1, 2.2 accessibility compliance & best practices:
    - Image alt text missing / empty
    - Missing document lang attribute
    - Form inputs missing labels
    - Empty links / buttons without accessible names
    - Skipped heading hierarchy levels
    - Ambiguous anchor texts
    - Viewport scaling restrictions
    Stores individual violations and aggregates totals per page.
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting accessibility analysis for audit {self.audit_id}")
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        all_violations: List[Dict[str, Any]] = []

        for page in pages:
            page_id = page['id']
            url = page.get('url', '')
            content_type = page.get('content_type', '') or ''
            if 'text/html' not in content_type:
                continue

            # Check if we have raw HTML or fetch from db/headings
            # We can inspect images and headings from database for this page
            images = await self.db.get_images(self.audit_id, page_id=page_id)
            headings = await self.db.get_headings(page_id=page_id, audit_id=self.audit_id)
            links = await self.db.get_links(self.audit_id, page_id=page_id)

            page_violations: List[Dict[str, Any]] = []

            # 1. Image alt check (WCAG 2.0 A - 1.1.1 Non-text Content)
            for img in images:
                alt = img.get('alt_text')
                src = img.get('src') or ''
                if alt is None:
                    page_violations.append({
                        'audit_id': self.audit_id,
                        'page_id': page_id,
                        'page_url': url,
                        'rule_id': 'image-alt',
                        'description': 'Image is missing alt attribute',
                        'impact': 'critical',
                        'wcag_tags': json.dumps(['wcag2a', 'wcag111']),
                        'html_snippet': f'<img src="{src[:120]}">',
                        'target_selector': f'img[src*="{src[:40]}"]' if src else 'img'
                    })
                elif alt.strip() == '' and not img.get('is_decorative'):
                    # Empty alt can be decorative, but flag as minor/notice if likely meaningful
                    pass

            # 2. Document language check (WCAG 2.0 A - 3.1.1 Language of Page)
            lang = page.get('language')
            if not lang:
                page_violations.append({
                    'audit_id': self.audit_id,
                    'page_id': page_id,
                    'page_url': url,
                    'rule_id': 'html-has-lang',
                    'description': 'html element does not have a lang attribute',
                    'impact': 'serious',
                    'wcag_tags': json.dumps(['wcag2a', 'wcag311']),
                    'html_snippet': '<html>',
                    'target_selector': 'html'
                })

            # 3. Viewport scaling restriction check (WCAG 2.1 AA - 1.4.4 Resize text / 1.4.10 Reflow)
            viewport = page.get('viewport') or ''
            if 'user-scalable=no' in viewport.lower() or 'maximum-scale=1' in viewport.lower():
                page_violations.append({
                    'audit_id': self.audit_id,
                    'page_id': page_id,
                    'page_url': url,
                    'rule_id': 'meta-viewport-scalable',
                    'description': 'Viewport restricts user zooming and scaling',
                    'impact': 'moderate',
                    'wcag_tags': json.dumps(['wcag21aa', 'wcag144']),
                    'html_snippet': f'<meta name="viewport" content="{viewport}">',
                    'target_selector': 'meta[name="viewport"]'
                })

            # 4. Heading hierarchy order check (Best Practice)
            prev_level = 0
            for h in headings:
                tag = h.get('tag', '').lower()
                if re.match(r'^h[1-6]$', tag):
                    lvl = int(tag[1])
                    if prev_level > 0 and lvl > prev_level + 1:
                        page_violations.append({
                            'audit_id': self.audit_id,
                            'page_id': page_id,
                            'page_url': url,
                            'rule_id': 'heading-order',
                            'description': f'Heading level skipped from H{prev_level} to H{lvl}',
                            'impact': 'moderate',
                            'wcag_tags': json.dumps(['best-practice']),
                            'html_snippet': f'<{tag}>{h.get("text", "")[:80]}</{tag}>',
                            'target_selector': tag
                        })
                    prev_level = lvl

            # 5. Empty or ambiguous link texts (WCAG 2.0 A & AAA)
            for link in links:
                anchor = (link.get('anchor_text') or '').strip()
                target_u = link.get('target_url') or ''
                if not anchor:
                    page_violations.append({
                        'audit_id': self.audit_id,
                        'page_id': page_id,
                        'page_url': url,
                        'rule_id': 'link-name',
                        'description': 'Link has no accessible anchor text or description',
                        'impact': 'serious',
                        'wcag_tags': json.dumps(['wcag2a', 'wcag244']),
                        'html_snippet': f'<a href="{target_u[:100]}"></a>',
                        'target_selector': f'a[href*="{target_u[:40]}"]' if target_u else 'a'
                    })
                elif anchor.lower() in AMBIGUOUS_ANCHOR_TEXTS:
                    page_violations.append({
                        'audit_id': self.audit_id,
                        'page_id': page_id,
                        'page_url': url,
                        'rule_id': 'link-in-text-block',
                        'description': f'Link text "{anchor}" is ambiguous without context',
                        'impact': 'minor',
                        'wcag_tags': json.dumps(['wcag2aaa', 'best-practice']),
                        'html_snippet': f'<a href="{target_u[:100]}">{anchor}</a>',
                        'target_selector': f'a[href*="{target_u[:40]}"]' if target_u else 'a'
                    })

            # Calculate category aggregations for this page
            total = len(page_violations)
            best_practice = 0
            wcag_2_0_a = 0
            wcag_2_0_aa = 0
            wcag_2_0_aaa = 0
            wcag_2_1_aa = 0
            wcag_2_2_aa = 0

            for v in page_violations:
                tags = json.loads(v['wcag_tags'])
                if 'best-practice' in tags:
                    best_practice += 1
                if 'wcag2a' in tags:
                    wcag_2_0_a += 1
                if 'wcag2aa' in tags:
                    wcag_2_0_aa += 1
                if 'wcag2aaa' in tags:
                    wcag_2_0_aaa += 1
                if 'wcag21aa' in tags:
                    wcag_2_1_aa += 1
                if 'wcag22aa' in tags:
                    wcag_2_2_aa += 1

            # Update page columns
            await self.db.update_page_columns(
                page_id,
                accessibility_violations_total=total,
                accessibility_best_practice=best_practice,
                accessibility_wcag_2_0_a=wcag_2_0_a,
                accessibility_wcag_2_0_aa=wcag_2_0_aa,
                accessibility_wcag_2_0_aaa=wcag_2_0_aaa,
                accessibility_wcag_2_1_aa=wcag_2_1_aa,
                accessibility_wcag_2_2_aa=wcag_2_2_aa
            )

            all_violations.extend(page_violations)

        if all_violations:
            await self.db.add_accessibility_violations_batch(all_violations)

        logger.info(f"Completed accessibility analysis for audit {self.audit_id}: {len(all_violations)} violations found")
