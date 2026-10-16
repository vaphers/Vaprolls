import re
import json
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
try:
    from lxml import html as lxml_html
    from lxml import etree as lxml_etree
except ImportError:
    lxml_html = None
    lxml_etree = None

logger = logging.getLogger(__name__)

class CustomExtractorEngine:
    """Evaluates user-defined XPath, CSS, and Regex custom extraction and custom search rules."""

    @staticmethod
    def extract_custom_data(
        html_content: str,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extracts data from HTML according to user rules.
        
        Rule structure:
        {
            "name": "Product Price",
            "type": "css" | "xpath" | "regex",
            "expression": ".price, span.amount",
            "extract_type": "text" | "html" | "attribute",
            "attribute_name": "content"
        }
        """
        if not html_content or not rules:
            return {}

        results = {}
        soup = None
        tree = None

        for rule in rules:
            name = rule.get("name", "").strip()
            rule_type = rule.get("type", "css").lower()
            expression = rule.get("expression", "").strip()
            extract_type = rule.get("extract_type", "text").lower()
            attr_name = rule.get("attribute_name", "").strip()

            if not name or not expression:
                continue

            try:
                extracted_values = []

                if rule_type == "regex":
                    matches = re.findall(expression, html_content, flags=re.IGNORECASE | re.DOTALL)
                    if matches:
                        for m in matches[:5]:
                            val = m if isinstance(m, str) else (m[0] if isinstance(m, tuple) and m else "")
                            if val:
                                extracted_values.append(val.strip())

                elif rule_type == "xpath" and lxml_html is not None:
                    if tree is None:
                        tree = lxml_html.fromstring(html_content)
                    elements = tree.xpath(expression)
                    for el in elements[:5]:
                        if isinstance(el, str):
                            extracted_values.append(el.strip())
                        elif hasattr(el, 'text_content'):
                            if extract_type == "text":
                                extracted_values.append(el.text_content().strip())
                            elif extract_type == "html":
                                extracted_values.append(lxml_etree.tostring(el, encoding='unicode').strip())
                            elif extract_type == "attribute" and attr_name:
                                val = el.get(attr_name, "")
                                if val:
                                    extracted_values.append(val.strip())

                elif rule_type == "css":
                    if soup is None:
                        soup = BeautifulSoup(html_content, 'html.parser')
                    elements = soup.select(expression)
                    for el in elements[:5]:
                        if extract_type == "text":
                            extracted_values.append(el.get_text(strip=True))
                        elif extract_type == "html":
                            extracted_values.append(str(el))
                        elif extract_type == "attribute" and attr_name:
                            val = el.get(attr_name, "")
                            if val:
                                extracted_values.append(str(val).strip())

                # Join multiple matches with semicolon if multiple found
                if extracted_values:
                    results[name] = " | ".join(extracted_values)
                else:
                    results[name] = ""

            except Exception as e:
                logger.debug(f"Custom extraction error for {name} ({expression}): {e}")
                results[name] = ""

        return results

    @staticmethod
    def search_custom_data(
        html_content: str,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Searches HTML for 'contains' or 'does_not_contain' queries.
        
        Rule structure:
        {
            "name": "GA4 Tag",
            "condition": "contains" | "does_not_contain",
            "query": "G-[A-Z0-9]+",
            "regex": true
        }
        """
        if not html_content or not rules:
            return {}

        results = {}
        for rule in rules:
            name = rule.get("name", "").strip()
            condition = rule.get("condition", "contains").lower()
            query = rule.get("query", "").strip()
            is_regex = bool(rule.get("regex", False))

            if not name or not query:
                continue

            try:
                matches = []
                if is_regex:
                    matches = list(re.finditer(query, html_content, flags=re.IGNORECASE))
                else:
                    idx = 0
                    q_lower = query.lower()
                    h_lower = html_content.lower()
                    while True:
                        idx = h_lower.find(q_lower, idx)
                        if idx == -1:
                            break
                        matches.append(idx)
                        idx += len(q_lower)

                match_count = len(matches)
                has_matches = match_count > 0

                if condition == "contains":
                    matched = has_matches
                else:  # does_not_contain
                    matched = not has_matches

                # Extract first snippet if matched
                snippet = ""
                if has_matches:
                    start_pos = matches[0].start() if is_regex else matches[0]
                    s_min = max(0, start_pos - 40)
                    s_max = min(len(html_content), start_pos + len(query) + 40)
                    snippet = html_content[s_min:s_max].replace("\n", " ").strip()

                results[name] = {
                    "matched": matched,
                    "condition": condition,
                    "count": match_count,
                    "snippet": snippet[:160] if snippet else ""
                }
            except Exception as e:
                logger.debug(f"Custom search error for {name} ({query}): {e}")
                results[name] = {
                    "matched": False,
                    "condition": condition,
                    "count": 0,
                    "snippet": ""
                }

        return results

