"""
Social Meta Analyzer for Vaprolls SEO Spider.
Audits Open Graph and Twitter Card tags across crawled pages.
"""
import logging
from typing import Optional, Any, Dict, List
from database.db import Database

logger = logging.getLogger(__name__)

class SocialMetaAnalyzer:
    """
    Audits Open Graph and Twitter Card metadata:
    - Missing og:title, og:description, og:image, og:type
    - Missing twitter:card, twitter:title, twitter:description, twitter:image
    - Duplicate OG titles across multiple pages
    - Incomplete social snippet previews
    - Site-wide social meta tag coverage
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting social meta analysis for audit {self.audit_id}")
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            return

        total_html = 0
        has_og_title_count = 0
        has_og_image_count = 0
        has_og_desc_count = 0
        has_twitter_card_count = 0
        has_complete_og_count = 0

        og_titles_map: Dict[str, List[str]] = {}

        for page in pages:
            content_type = (page.get('content_type') or '').lower()
            if 'text/html' not in content_type and page.get('html_size', 0) == 0:
                continue

            url = page.get('url', '')
            if not url:
                continue

            page_id = page.get('id')
            total_html += 1

            og_title = page.get('og_title')
            og_desc = page.get('og_description')
            og_image = page.get('og_image')
            og_type = page.get('og_type')

            twitter_card = page.get('twitter_card')
            twitter_title = page.get('twitter_title')
            twitter_desc = page.get('twitter_description')
            twitter_image = page.get('twitter_image')

            # Track duplicate OG titles
            if og_title:
                og_titles_map.setdefault(og_title.strip(), []).append(url)
                has_og_title_count += 1
            if og_desc:
                has_og_desc_count += 1
            if og_image:
                has_og_image_count += 1
            if twitter_card:
                has_twitter_card_count += 1

            is_og_complete = bool(og_title and og_desc and og_image)
            if is_og_complete:
                has_complete_og_count += 1

            # Page-level issues
            if not og_title:
                await self._add_issue(
                    page_id, url, 'warning', 'missing_og_title',
                    "Missing Open Graph title tag (og:title)",
                    "Add <meta property='og:title' content='...'> so social networks display the correct headline when shared.",
                    None
                )
            elif len(og_title) > 95:
                await self._add_issue(
                    page_id, url, 'info', 'long_og_title',
                    f"Open Graph title is {len(og_title)} chars (recommended < 95 chars)",
                    "Keep og:title concise to prevent truncation on Facebook and LinkedIn.",
                    og_title
                )

            if not og_desc:
                await self._add_issue(
                    page_id, url, 'info', 'missing_og_description',
                    "Missing Open Graph description tag (og:description)",
                    "Add <meta property='og:description' content='...'> to provide a compelling snippet on social networks.",
                    None
                )

            if not og_image:
                await self._add_issue(
                    page_id, url, 'warning', 'missing_og_image',
                    "Missing Open Graph image tag (og:image)",
                    "Add an og:image (recommended 1200x630px) to ensure rich visual card previews when links are shared.",
                    None
                )

            if not og_type:
                await self._add_issue(
                    page_id, url, 'info', 'missing_og_type',
                    "Missing Open Graph type (og:type)",
                    "Specify og:type ('website', 'article', or 'product') to help social graphs classify your content.",
                    None
                )

            # Twitter Cards
            if not twitter_card:
                await self._add_issue(
                    page_id, url, 'info', 'missing_twitter_card',
                    "Missing Twitter Card tag (twitter:card)",
                    "Add <meta name='twitter:card' content='summary_large_image'> to enable rich media cards on X/Twitter.",
                    None
                )
            else:
                card_val = twitter_card.lower().strip()
                if card_val not in ('summary', 'summary_large_image', 'app', 'player'):
                    await self._add_issue(
                        page_id, url, 'warning', 'invalid_twitter_card',
                        f"Unrecognized twitter:card value '{twitter_card}'",
                        "Use 'summary' or 'summary_large_image' for standard web pages.",
                        twitter_card
                    )

        # Duplicate OG titles
        for title_str, urls in og_titles_map.items():
            if len(urls) > 1:
                sample_urls = urls[:5]
                await self._add_issue(
                    None, None, 'warning', 'duplicate_og_title',
                    f"Duplicate og:title found across {len(urls)} pages: '{title_str[:60]}...'",
                    "Customize og:title uniquely per page to give shared content a distinct identity.",
                    sample_urls
                )

        # Site-wide Coverage
        if total_html > 0:
            complete_og_pct = round((has_complete_og_count / total_html) * 100, 1)
            tw_card_pct = round((has_twitter_card_count / total_html) * 100, 1)
            og_img_pct = round((has_og_image_count / total_html) * 100, 1)

            severity = 'info' if complete_og_pct >= 80 else ('warning' if complete_og_pct >= 40 else 'critical')
            await self._add_issue(
                None, None, severity, 'social_meta_summary',
                f"Social Meta Coverage: {complete_og_pct}% complete OG ({has_complete_og_count}/{total_html}), {tw_card_pct}% Twitter cards",
                "Ensure every indexable page contains complete Open Graph and Twitter Card tags.",
                {
                    'total_html_pages': total_html,
                    'complete_og_pct': complete_og_pct,
                    'og_title_pct': round((has_og_title_count / total_html) * 100, 1),
                    'og_image_pct': og_img_pct,
                    'og_desc_pct': round((has_og_desc_count / total_html) * 100, 1),
                    'twitter_card_pct': tw_card_pct
                }
            )

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='social',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=element
        )
