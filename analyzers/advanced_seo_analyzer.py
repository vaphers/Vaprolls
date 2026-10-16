import re
import json
import logging
from typing import Dict, Any, List, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AdvancedSEOAnalyzer:
    """Audits Hreflang reciprocity, Structured Data schemas, and traces multi-hop Redirect Chains."""

    def __init__(self, database, audit_id: str):
        self.db = database
        self.audit_id = audit_id

    async def analyze(self):
        try:
            pages = await self.db.get_pages(self.audit_id)
            if not pages:
                return

            url_to_page = {p["url"]: p for p in pages}

            await self._audit_redirect_chains(pages, url_to_page)
            await self._audit_hreflang(pages, url_to_page)
            await self._audit_structured_data(pages)

            logger.info(f"[AdvancedSEOAnalyzer] Completed advanced SEO analysis for audit {self.audit_id}")
        except Exception as e:
            logger.error(f"AdvancedSEOAnalyzer error for {self.audit_id}: {e}", exc_info=True)

    async def _audit_redirect_chains(self, pages: List[Dict[str, Any]], url_to_page: Dict[str, Dict[str, Any]]):
        """Traces full hop-by-hop redirection paths and identifies loops/chains."""
        for page in pages:
            status = page.get("status_code", 0)
            if status not in (301, 302, 303, 307, 308) and not page.get("redirect_url"):
                continue

            curr_url = page["url"]
            visited = [curr_url]
            chain = [{"url": curr_url, "status_code": status}]
            is_loop = False

            dest = page.get("redirect_url")
            while dest and len(chain) < 10:
                target_page = url_to_page.get(dest)
                target_status = target_page.get("status_code", 200) if target_page else 200
                chain.append({"url": dest, "status_code": target_status})

                if dest in visited:
                    is_loop = True
                    break
                visited.append(dest)

                if target_page and target_page.get("status_code") in (301, 302, 303, 307, 308) and target_page.get("redirect_url"):
                    dest = target_page.get("redirect_url")
                else:
                    break

            chain_json = json.dumps(chain)
            await self.db.update_page_columns(page["id"], redirect_chain_json=chain_json)

            hops = len(chain) - 1
            if is_loop:
                await self.db.add_issue(
                    self.audit_id,
                    page_id=page["id"],
                    issue_type="redirect_loop",
                    category="Redirects",
                    severity="critical",
                    title="Redirect Loop Detected",
                    description=f"The URL '{curr_url}' redirects in a loop back to an earlier URL in the chain.",
                    recommendation="Ensure the URL redirects directly to the final 200 OK destination without circular hops."
                )
            elif hops > 1:
                await self.db.add_issue(
                    self.audit_id,
                    page_id=page["id"],
                    issue_type="redirect_chain",
                    category="Redirects",
                    severity="medium",
                    title=f"Redirect Chain ({hops} Hops)",
                    description=f"The URL '{curr_url}' takes {hops} redirects to reach the destination: {' -> '.join([c['url'] for c in chain])}",
                    recommendation="Update internal links and server redirects to point directly to the destination URL in a single 301 hop."
                )

    async def _audit_hreflang(self, pages: List[Dict[str, Any]], url_to_page: Dict[str, Dict[str, Any]]):
        """Validates hreflang reciprocity and language codes."""
        # Query hreflangs from database if available
        try:
            hreflangs = await self.db.get_hreflangs(self.audit_id)
        except Exception:
            hreflangs = []

        if not hreflangs:
            return

        # Map: page_url -> list of {lang, href}
        page_hreflangs: Dict[str, List[Dict[str, str]]] = {}
        for h in hreflangs:
            p_url = h.get("page_url")
            if p_url:
                if p_url not in page_hreflangs:
                    page_hreflangs[p_url] = []
                page_hreflangs[p_url].append({
                    "lang": (h.get("lang_code") or "").lower().strip(),
                    "href": h.get("target_url") or ""
                })

        for p_url, tags in page_hreflangs.items():
            page = url_to_page.get(p_url)
            if not page:
                continue

            page_id = page["id"]
            issues = []
            has_self = False

            for tag in tags:
                lang = tag["lang"]
                tgt = tag["href"]

                # 1. Format Check (e.g. en, en-us, es, de, x-default)
                if lang != "x-default" and not re.match(r'^[a-z]{2}(-[a-z]{2,4})?$', lang):
                    issues.append(f"Invalid language format: '{lang}' for target {tgt}")

                # 2. Check if self-referential
                if tgt == p_url:
                    has_self = True

                # 3. Check Target Status
                tgt_page = url_to_page.get(tgt)
                if tgt_page:
                    sc = tgt_page.get("status_code", 200)
                    if sc >= 400:
                        issues.append(f"Hreflang target returns HTTP {sc}: {tgt}")
                    elif sc in (301, 302, 307, 308):
                        issues.append(f"Hreflang target redirects ({sc}): {tgt}")
                
                # 4. Check Reciprocal Return Tag
                if tgt in page_hreflangs and tgt != p_url:
                    tgt_tags = page_hreflangs[tgt]
                    reciprocal = any(t["href"] == p_url for t in tgt_tags)
                    if not reciprocal:
                        issues.append(f"Missing reciprocal return hreflang tag on {tgt}")

            if not has_self and tags:
                issues.append("Missing self-referential hreflang tag")

            if issues:
                await self.db.update_page_columns(page_id, hreflang_issues_json=json.dumps(issues))
                for iss in issues[:3]:
                    await self.db.add_issue(
                        self.audit_id,
                        page_id=page_id,
                        issue_type="hreflang_error",
                        category="Localization",
                        severity="medium",
                        title="Hreflang Implementation Issue",
                        description=f"Page {p_url}: {iss}",
                        recommendation="Follow Google's hreflang guidelines: include return tags, self-referential tags, and use valid ISO codes."
                    )

    async def _audit_structured_data(self, pages: List[Dict[str, Any]]):
        """Audits JSON-LD structured data and schema types."""
        try:
            sd_items = await self.db.get_structured_data(self.audit_id)
        except Exception:
            sd_items = []

        page_sd_map: Dict[int, List[Dict[str, Any]]] = {}
        for item in sd_items:
            pid = item.get("page_id")
            if pid:
                if pid not in page_sd_map:
                    page_sd_map[pid] = []
                page_sd_map[pid].append(item)

        for page in pages:
            pid = page["id"]
            items = page_sd_map.get(pid, [])
            validations = []

            for item in items:
                raw_json = item.get("raw_json", "")
                schema_type = item.get("schema_type", "")

                if raw_json:
                    try:
                        parsed = json.loads(raw_json)
                        st = schema_type or (parsed.get("@type") if isinstance(parsed, dict) else "")
                        validations.append({
                            "type": str(st),
                            "valid_syntax": True,
                            "properties_count": len(parsed) if isinstance(parsed, dict) else 0
                        })
                    except Exception as e:
                        validations.append({
                            "type": schema_type or "Unknown",
                            "valid_syntax": False,
                            "error": str(e)
                        })
                        await self.db.add_issue(
                            self.audit_id,
                            page_id=pid,
                            issue_type="invalid_schema_syntax",
                            category="Structured Data",
                            severity="high",
                            title="Invalid JSON-LD Syntax",
                            description=f"JSON-LD syntax error on page: {e}",
                            recommendation="Ensure JSON-LD block is valid, properly formatted JSON without unescaped characters."
                        )

            if validations:
                await self.db.update_page_columns(pid, schema_validation_json=json.dumps(validations))

