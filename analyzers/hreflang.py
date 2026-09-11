import logging
import re
from typing import Dict, Any, List, Set
from database.db import Database

logger = logging.getLogger(__name__)

# Basic ISO 639-1 / 3166-1 language-country regex
HREFLANG_PATTERN = re.compile(r'^(?:[a-z]{2}(?:-[a-z]{2}|-[A-Z]{2})?|x-default)$')

class HreflangAnalyzer:
    """
    Validates complete cross-page hreflang configuration including bidirectional reciprocity,
    self-referencing tags, ISO 639-1/3166-1 syntax, target status codes, and x-default presence.
    """
    def __init__(self, db: Database, audit_id: str):
        self.db = db
        self.audit_id = audit_id

    async def analyze(self):
        logger.info(f"Starting Hreflang Matrix analysis for audit {self.audit_id}")
        tags = await self.db.get_hreflang_tags(self.audit_id)
        if not tags:
            logger.info("No hreflang tags found for this audit.")
            return

        pages = await self.db.get_pages(self.audit_id)
        url_to_page = {p['url']: p for p in pages}

        # Group tags by source URL
        source_groups: Dict[str, List[Dict[str, Any]]] = {}
        for tag in tags:
            source = tag['source_url']
            source_groups.setdefault(source, []).append(tag)

        # Build bidirectional verification map: (source, target) -> lang_code
        pairs: Dict[tuple[str, str], str] = {}
        for tag in tags:
            pairs[(tag['source_url'], tag['target_url'])] = tag['lang_code'].lower()

        for source_url, tag_list in source_groups.items():
            source_page = url_to_page.get(source_url)
            page_id = source_page['id'] if source_page else None

            has_self_ref = False
            has_x_default = False

            for tag in tag_list:
                target_url = tag['target_url']
                lang = tag['lang_code'].strip()
                lower_lang = lang.lower()

                # 1. Self reference check
                if target_url == source_url:
                    has_self_ref = True

                # 2. x-default check
                if lower_lang == 'x-default':
                    has_x_default = True

                # 3. ISO code validation
                if not HREFLANG_PATTERN.match(lang):
                    await self.db.add_issue(
                        audit_id=self.audit_id,
                        page_id=page_id,
                        url=source_url,
                        category='technical',
                        severity='warning',
                        issue_type='hreflang_invalid_code',
                        message=f"Invalid hreflang language/region code: '{lang}'",
                        recommendation="Format hreflang codes using ISO 639-1 for language (e.g. 'en') and optional ISO 3166-1 Alpha 2 for region (e.g. 'en-US'), or 'x-default'.",
                        element=f"hreflang='{lang}' href='{target_url}'"
                    )

                # 4. Target status check
                if target_url in url_to_page:
                    target_status = url_to_page[target_url].get('status_code', 200)
                    if target_status >= 400:
                        await self.db.add_issue(
                            audit_id=self.audit_id,
                            page_id=page_id,
                            url=source_url,
                            category='technical',
                            severity='critical',
                            issue_type='hreflang_broken_target',
                            message=f"Hreflang alternate points to broken URL ({target_status}): {target_url}",
                            recommendation="Update or remove alternate hreflang tags that point to non-200 URLs.",
                            element=target_url
                        )
                    elif target_status in (301, 302, 307, 308):
                        await self.db.add_issue(
                            audit_id=self.audit_id,
                            page_id=page_id,
                            url=source_url,
                            category='technical',
                            severity='warning',
                            issue_type='hreflang_redirected_target',
                            message=f"Hreflang alternate points to a redirected URL ({target_status}): {target_url}",
                            recommendation="Always link directly to the final canonical destination URL in hreflang tags, bypassing redirects.",
                            element=target_url
                        )

                # 5. Bidirectional reciprocity check
                if target_url != source_url and lower_lang != 'x-default':
                    # Does target_url have an alternate pointing back to source_url?
                    if (target_url, source_url) not in pairs:
                        await self.db.add_issue(
                            audit_id=self.audit_id,
                            page_id=page_id,
                            url=source_url,
                            category='technical',
                            severity='critical',
                            issue_type='hreflang_no_return_tag',
                            message=f"Missing return hreflang tag: '{target_url}' does not point back to '{source_url}'",
                            recommendation="Ensure bidirectional reciprocity: if Page A specifies Page B as an alternate, Page B must specify Page A in return.",
                            element=f"Target: {target_url} (lang: {lang})"
                        )

            # Check for missing self reference
            if not has_self_ref:
                await self.db.add_issue(
                    audit_id=self.audit_id,
                    page_id=page_id,
                    url=source_url,
                    category='technical',
                    severity='warning',
                    issue_type='hreflang_missing_self_reference',
                    message="Hreflang annotations are missing a self-referencing tag for this URL",
                    recommendation="Google requires every localized page with hreflang annotations to include a self-referencing hreflang tag.",
                    element=source_url
                )

            # Check for missing x-default on multi-alternate pages
            if len(tag_list) > 1 and not has_x_default:
                await self.db.add_issue(
                    audit_id=self.audit_id,
                    page_id=page_id,
                    url=source_url,
                    category='technical',
                    severity='info',
                    issue_type='hreflang_missing_x_default',
                    message="International page set is missing an 'x-default' fallback tag",
                    recommendation="Add an hreflang='x-default' tag pointing to the international landing page or language selector for users outside targeted regions.",
                    element=source_url
                )

        logger.info(f"Hreflang matrix validation completed for audit {self.audit_id}")
