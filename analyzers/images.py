import logging
from typing import Optional, Any
from database.db import Database

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting image analysis for audit {self.audit_id}")
        
        images = await self.db.get_images(self.audit_id)
        if not images:
            logger.info(f"No images found for audit {self.audit_id}")
            return

        missing_alt_count = 0
        old_format_images = 0

        for img in images:
            page_id = img.get('page_id')
            page_url = img.get('page_url')
            src = img.get('src')
            alt_text = img.get('alt_text')
            has_dimensions = img.get('has_dimensions')
            is_broken = img.get('is_broken')
            is_lazy_loaded = img.get('is_lazy_loaded')

            if alt_text is None:
                await self._add_issue(page_id, page_url, 'warning', 'missing_alt', "Image missing alt attribute", "Add descriptive alt text to the image.", src)
                missing_alt_count += 1
            elif alt_text == '':
                await self._add_issue(page_id, page_url, 'info', 'empty_alt', "Image has empty alt text", "Ensure this is a decorative image, otherwise add alt text.", src)
            elif len(alt_text) > 125:
                await self._add_issue(page_id, page_url, 'info', 'long_alt', "Alt text > 125 characters", "Keep alt text concise (under 125 characters).", src)

            if has_dimensions is False:
                await self._add_issue(page_id, page_url, 'warning', 'missing_dimensions', "Missing dimensions causes CLS", "Specify explicit width and height attributes.", src)

            if is_broken:
                await self._add_issue(page_id, page_url, 'critical', 'broken_image', "Broken image detected", "Fix or remove the broken image link.", src)

            if is_lazy_loaded is False:
                await self._add_issue(page_id, page_url, 'info', 'not_lazy_loaded', "Image not lazy-loaded", "Consider adding loading='lazy' attribute.", src)

            if src:
                src_lower = src.lower()
                if any(bad_name in src_lower for bad_name in ['img_', 'dsc_', 'screenshot_']) or src.split('/')[-1].split('.')[0].isdigit():
                    await self._add_issue(page_id, page_url, 'info', 'non_descriptive_filename', "Non-descriptive image filename", "Use descriptive keywords in image filenames.", src)

                if src_lower.endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    await self._add_issue(page_id, page_url, 'info', 'old_image_format', "Image using old format", "Consider serving images in next-gen formats like WebP or AVIF.", src)
                    old_format_images += 1

            # Check image file size
            file_size = img.get('file_size')
            if file_size:
                size_kb = file_size / 1024
                if size_kb > 200:
                    await self._add_issue(
                        page_id, page_url, 'critical', 'oversized_image',
                        f"Image is {size_kb:.0f}KB (>200KB limit)",
                        "Compress, resize, or convert this image to WebP/AVIF to reduce load times.",
                        src
                    )
                elif size_kb > 100:
                    await self._add_issue(
                        page_id, page_url, 'warning', 'large_image',
                        f"Image is {size_kb:.0f}KB (>100KB)",
                        "Consider compressing this image to under 100KB.",
                        src
                    )

        if missing_alt_count > 0:
            await self._add_issue(None, None, 'warning', 'site_wide_missing_alt', f"{missing_alt_count} images missing alt text", "Review and add alt text to missing images.", missing_alt_count)

        if old_format_images > 0:
            await self._add_issue(None, None, 'info', 'site_wide_old_formats', f"{old_format_images} images using old formats", "Upgrade images to next-gen formats.", old_format_images)

        if hasattr(self, 'issues_buffer') and self.issues_buffer:
            await self.db.add_issues_batch(self.issues_buffer)
            self.issues_buffer = []

    async def _add_issue(self, page_id: Optional[int], url: Optional[str], severity: str, issue_type: str, message: str, recommendation: str, element: Any = None):
        if not hasattr(self, 'issues_buffer'):
            self.issues_buffer = []
        self.issues_buffer.append({
            'audit_id': self.audit_id,
            'page_id': page_id,
            'url': url,
            'category': 'images',
            'severity': severity,
            'issue_type': issue_type,
            'message': message,
            'recommendation': recommendation,
            'element': element
        })
        if len(self.issues_buffer) >= 500:
            await self.db.add_issues_batch(self.issues_buffer)
            self.issues_buffer = []
