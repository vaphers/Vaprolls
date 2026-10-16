import io
import csv
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import List, Dict, Any

class ExportGenerator:
    """Generates valid XML Sitemaps and bulk relational CSV exports."""

    @staticmethod
    def generate_sitemap_xml(pages: List[Dict[str, Any]], domain: str = "") -> str:
        """Generates standard compliant sitemap.xml for 200 OK indexable canonical pages."""
        urlset = ET.Element('urlset', {
            'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd'
        })

        now_str = datetime.utcnow().strftime('%Y-%m-%d')

        for p in pages:
            url = p.get('url', '')
            status = p.get('status_code', 0)
            is_indexable = bool(p.get('is_indexable', True))
            content_type = (p.get('content_type') or '').lower()
            canonical_url = p.get('canonical_url') or ''

            # Include only 200 OK, HTML, indexable canonical URLs
            if status == 200 and is_indexable and ('html' in content_type or not content_type):
                if canonical_url and canonical_url != url:
                    continue  # Skip canonicalised non-canonical duplicates

                url_el = ET.SubElement(urlset, 'url')
                loc_el = ET.SubElement(url_el, 'loc')
                loc_el.text = url

                lastmod_el = ET.SubElement(url_el, 'lastmod')
                lastmod_el.text = now_str

                changefreq_el = ET.SubElement(url_el, 'changefreq')
                changefreq_el.text = 'weekly'

                priority_el = ET.SubElement(url_el, 'priority')
                depth = p.get('click_depth') or p.get('crawl_depth') or 0
                priority_el.text = '1.0' if depth == 0 else ('0.8' if depth == 1 else '0.6')

        raw_xml = ET.tostring(urlset, encoding='utf-8')
        reparsed = minidom.parseString(raw_xml)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

    @staticmethod
    def export_all_inlinks(links: List[Dict[str, Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Source URL", "Target URL", "Anchor Text", "Link Type", "Follow/Nofollow", "Is Internal"])
        for l in links:
            writer.writerow([
                l.get("source_url", ""),
                l.get("target_url", ""),
                l.get("anchor_text", ""),
                l.get("link_type", "Hyperlink"),
                "Nofollow" if l.get("nofollow") else "Follow",
                "Internal" if l.get("is_internal") else "External"
            ])
        return output.getvalue()

    @staticmethod
    def export_all_images(images: List[Dict[str, Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Page URL", "Image Source", "Alt Text", "Width", "Height", "Format", "Missing Alt"])
        for img in images:
            alt = img.get("alt_text") or ""
            writer.writerow([
                img.get("page_url", ""),
                img.get("src", ""),
                alt,
                img.get("width") or "",
                img.get("height") or "",
                img.get("format") or "",
                "Missing" if not alt.strip() else "OK"
            ])
        return output.getvalue()

    @staticmethod
    def export_redirect_chains(pages: List[Dict[str, Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Source URL", "Status Code", "Redirect URL", "Hops Count", "Chain Details"])
        for p in pages:
            sc = p.get("status_code", 0)
            chain_raw = p.get("redirect_chain_json")
            if sc in (301, 302, 303, 307, 308) or chain_raw:
                chain = []
                if chain_raw:
                    try: chain = json.loads(chain_raw)
                    except: pass
                hops = len(chain) - 1 if chain else 1
                details = " -> ".join([f"{c['url']} ({c.get('status_code', '')})" for c in chain]) if chain else p.get("redirect_url", "")
                writer.writerow([
                    p.get("url", ""),
                    sc,
                    p.get("redirect_url", ""),
                    hops,
                    details
                ])
        return output.getvalue()

