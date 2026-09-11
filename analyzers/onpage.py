import logging
from typing import List, Dict, Any, Optional
from database.db import Database

logger = logging.getLogger(__name__)

class OnPageAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting On-Page Analysis for audit {self.audit_id}")
        pages = await self.db.get_pages(self.audit_id)
        if not pages:
            logger.warning(f"No pages found for audit {self.audit_id}")
            return

        titles = {}
        meta_descriptions = {}
        h1s = {}
        content_hashes = {}
        thin_content_count = 0
        total_word_count = 0
        pages_with_words = 0

        for page in pages:
            page_id = page['id']
            url = page['url']
            
            # Title Checks
            title = page.get('title')
            if not title or not title.strip():
                await self._add_issue(
                    page_id, url, 'critical', 'missing_title',
                    'Missing title tag',
                    'Add a unique, descriptive title tag between 30-60 characters that includes your target keyword.'
                )
            else:
                title = title.strip()
                length = len(title)
                if length < 30:
                    await self._add_issue(
                        page_id, url, 'warning', 'title_too_short',
                        f'Title tag is too short ({length} chars)',
                        'Lengthen the title to 30-60 characters.'
                    )
                elif length > 60:
                    await self._add_issue(
                        page_id, url, 'warning', 'title_too_long',
                        f'Title tag is too long ({length} chars)',
                        f'Shorten the title to under 60 characters. Current length: {length} characters. Search engines will truncate it.'
                    )
                
                # We can't directly check for multiple titles if it's just a string field in DB, 
                # but site-wide duplicate title we can track.
                titles.setdefault(title, []).append((page_id, url))

            # Meta Description Checks
            meta_desc = page.get('meta_description')
            if not meta_desc or not meta_desc.strip():
                await self._add_issue(
                    page_id, url, 'warning', 'missing_meta_description',
                    'Missing meta description',
                    'Add a unique meta description between 70-160 characters.'
                )
            else:
                meta_desc = meta_desc.strip()
                length = len(meta_desc)
                if length < 70:
                    await self._add_issue(
                        page_id, url, 'warning', 'meta_description_too_short',
                        f'Meta description is too short ({length} chars)',
                        'Lengthen the meta description to 70-160 characters.'
                    )
                elif length > 160:
                    await self._add_issue(
                        page_id, url, 'warning', 'meta_description_too_long',
                        f'Meta description is too long ({length} chars)',
                        'Shorten the meta description to under 160 characters.'
                    )
                
                meta_descriptions.setdefault(meta_desc, []).append((page_id, url))

            # H1 Tag Checks
            h1 = page.get('h1')
            if not h1 or not h1.strip():
                await self._add_issue(
                    page_id, url, 'critical', 'missing_h1',
                    'Missing H1 tag',
                    'Add a single H1 tag to the page describing its main topic.'
                )
            else:
                h1 = h1.strip()
                length = len(h1)
                if length > 70:
                    await self._add_issue(
                        page_id, url, 'warning', 'h1_too_long',
                        f'H1 tag is too long ({length} chars)',
                        'Shorten the H1 tag to under 70 characters.'
                    )
                if title and h1.lower() == title.lower():
                    await self._add_issue(
                        page_id, url, 'info', 'h1_identical_to_title',
                        'H1 tag is identical to the title tag',
                        'Consider making the H1 tag slightly different from the title for better user experience.'
                    )
                
                h1s.setdefault(h1, []).append((page_id, url))

            # Headings Hierarchy Checks
            headings = await self.db.get_headings(page_id)
            if not headings:
                await self._add_issue(
                    page_id, url, 'warning', 'no_headings',
                    'No headings found on the page',
                    'Use heading tags (H1, H2, H3, etc.) to structure your content.'
                )
            else:
                if len(headings) > 30:
                    await self._add_issue(
                        page_id, url, 'info', 'too_many_headings',
                        f'Too many headings ({len(headings)})',
                        'Ensure headings are used properly and not overused.'
                    )

                h1_count = sum(1 for h in headings if h['tag'].lower() == 'h1')
                if h1_count > 1:
                    await self._add_issue(
                        page_id, url, 'warning', 'multiple_h1_tags',
                        f'Multiple H1 tags found ({h1_count})',
                        'Use only one H1 tag per page.'
                    )

                # Check hierarchy
                expected_level = 1
                for h in headings:
                    try:
                        level = int(h['tag'][1])
                        if level > expected_level + 1:
                            await self._add_issue(
                                page_id, url, 'warning', 'heading_hierarchy_violation',
                                f"Heading hierarchy skipped a level (H{expected_level} followed by H{level})",
                                'Ensure headings follow a logical hierarchy without skipping levels.'
                            )
                            break
                        expected_level = level
                    except ValueError:
                        pass

            # Content Checks
            word_count = page.get('word_count')
            if word_count is not None:
                total_word_count += word_count
                pages_with_words += 1
                if word_count < 100:
                    await self._add_issue(
                        page_id, url, 'critical', 'very_thin_content',
                        f'Very thin content ({word_count} words)',
                        'Add substantial content to this page (aim for 300+ words).'
                    )
                    thin_content_count += 1
                elif word_count < 300:
                    await self._add_issue(
                        page_id, url, 'warning', 'thin_content',
                        f'Thin content ({word_count} words)',
                        'Add more content to this page (aim for 300+ words).'
                    )
                    thin_content_count += 1
                
                html_size = page.get('html_size')
                if html_size and html_size > 0:
                    ratio = (word_count * 6) / html_size
                    if ratio < 0.1:
                        await self._add_issue(
                            page_id, url, 'info', 'low_text_to_html_ratio',
                            'Low text to HTML ratio',
                            'Consider adding more textual content or reducing unnecessary HTML/inline CSS/JS.'
                        )

            # Duplicate content tracker
            content_hash = page.get('content_hash')
            if content_hash:
                content_hashes.setdefault(content_hash, []).append((page_id, url))

        # Site-wide checks
        for title, duplicate_pages in titles.items():
            if len(duplicate_pages) > 1:
                urls = ", ".join([p[1] for p in duplicate_pages])
                for page_id, url in duplicate_pages:
                    await self._add_issue(
                        page_id, url, 'warning', 'duplicate_title',
                        'Duplicate title tag',
                        f'Create unique title tags for each page. These pages share the same title: {urls}'
                    )

        for meta_desc, duplicate_pages in meta_descriptions.items():
            if len(duplicate_pages) > 1:
                urls = ", ".join([p[1] for p in duplicate_pages])
                for page_id, url in duplicate_pages:
                    await self._add_issue(
                        page_id, url, 'warning', 'duplicate_meta_description',
                        'Duplicate meta description',
                        f'Create unique meta descriptions for each page. These pages share the same description: {urls}'
                    )

        for h1, duplicate_pages in h1s.items():
            if len(duplicate_pages) > 1:
                urls = ", ".join([p[1] for p in duplicate_pages])
                for page_id, url in duplicate_pages:
                    await self._add_issue(
                        page_id, url, 'info', 'duplicate_h1',
                        'Duplicate H1 tag',
                        f'Ensure H1 tags are unique across the site. Pages sharing this H1: {urls}'
                    )

        for content_hash, duplicate_pages in content_hashes.items():
            if len(duplicate_pages) > 1:
                urls = ", ".join([p[1] for p in duplicate_pages])
                for page_id, url in duplicate_pages:
                    await self._add_issue(
                        page_id, url, 'critical', 'duplicate_content',
                        'Duplicate content detected',
                        f'Ensure content is unique or use canonical tags. Pages with exact same content: {urls}'
                    )

        # Site-wide stats as info (not tied to a specific page_id)
        if pages_with_words > 0:
            avg_word_count = total_word_count // pages_with_words
            await self._add_issue(
                None, None, 'info', 'average_word_count',
                f'Average word count across site: {avg_word_count}',
                'Maintain a healthy amount of informative content across the site.'
            )
            if thin_content_count > 0:
                await self._add_issue(
                    None, None, 'info', 'thin_content_summary',
                    f'{thin_content_count} pages have thin content (< 300 words)',
                    'Review and expand pages with little content.'
                )

        logger.info(f"Completed On-Page Analysis for audit {self.audit_id}")

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str):
        await self.db.add_issue(
            audit_id=self.audit_id,
            page_id=page_id,
            url=url,
            category='onpage',
            severity=severity,
            issue_type=issue_type,
            message=message,
            recommendation=recommendation,
            element=None
        )
