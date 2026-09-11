import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

def detect_technologies(html: str = "", headers: Optional[Dict[str, str]] = None, url: str = "") -> Dict[str, List[str]]:
    """
    Detect technologies used on a webpage from HTML content, HTTP headers, and URL.
    Returns a dictionary of categories with detected technology names.
    """
    headers = {k.lower(): str(v) for k, v in (headers or {}).items()}
    html_lower = (html or "").lower()
    server_header = headers.get("server", "").lower()
    
    tech: Dict[str, List[str]] = {
        "cms": [],
        "framework": [],
        "server": [],
        "cdn": [],
        "analytics": [],
        "tag_manager": [],
        "marketing_trackers": []
    }
    
    # -------------------------------------------------------------
    # 1. CMS DETECTION
    # -------------------------------------------------------------
    if "cdn.shopify.com" in html_lower or "shopify.theme" in html_lower or "window.shopify" in html_lower or "myshopify.com" in html_lower:
        tech["cms"].append("Shopify")
    if "wp-content" in html_lower or "wp-includes" in html_lower or 'name="generator" content="wordpress' in html_lower:
        tech["cms"].append("WordPress")
    if "woocommerce" in html_lower or "wc-ajax" in html_lower:
        tech["cms"].append("WooCommerce")
    if "webflow" in html_lower or "data-wf-page" in html_lower:
        tech["cms"].append("Webflow")
    if "wix.com" in html_lower or "_wix" in html_lower or "wix-warmup-data" in html_lower:
        tech["cms"].append("Wix")
    if "squarespace" in html_lower or "static1.squarespace.com" in html_lower:
        tech["cms"].append("Squarespace")
    if "magento" in html_lower or "mage/cookies" in html_lower:
        tech["cms"].append("Magento")
    if "drupal" in html_lower or "drupal.settings" in html_lower:
        tech["cms"].append("Drupal")
    if "ghost.org" in html_lower or "ghost-root" in html_lower:
        tech["cms"].append("Ghost")
    if "prestashop" in html_lower:
        tech["cms"].append("PrestaShop")
    if not tech["cms"]:
        tech["cms"].append("Custom / Headless")

    # -------------------------------------------------------------
    # 2. SERVER & CDN DETECTION
    # -------------------------------------------------------------
    # Server
    if "cloudflare" in server_header:
        tech["server"].append("Cloudflare")
    elif "nginx" in server_header:
        tech["server"].append("Nginx")
    elif "apache" in server_header:
        tech["server"].append("Apache")
    elif "litespeed" in server_header:
        tech["server"].append("LiteSpeed")
    elif "openresty" in server_header:
        tech["server"].append("OpenResty")
    elif "caddy" in server_header:
        tech["server"].append("Caddy")
    elif "microsoft-iis" in server_header:
        tech["server"].append("Microsoft-IIS")
    elif server_header:
        tech["server"].append(headers.get("server", "Web Server"))
    else:
        tech["server"].append("Standard Web Server")

    # CDN
    if "cloudflare" in server_header or "cf-ray" in headers or "cf-cache-status" in headers:
        tech["cdn"].append("Cloudflare")
    if "fastly" in server_header or "x-fastly-request-id" in headers or "fastly" in headers.get("via", "").lower():
        tech["cdn"].append("Fastly")
    if "cloudfront" in str(headers) or "x-amz-cf-id" in headers or "cloudfront.net" in html_lower:
        tech["cdn"].append("Amazon CloudFront")
    if "cdn.shopify.com" in html_lower:
        tech["cdn"].append("Shopify CDN")
    if "akamai" in server_header or "x-akamai" in str(headers):
        tech["cdn"].append("Akamai")
    if "bunnycdn" in html_lower or "b-cdn.net" in html_lower:
        tech["cdn"].append("BunnyCDN")
    if not tech["cdn"]:
        tech["cdn"].append("Direct Origin (No CDN detected)")

    # -------------------------------------------------------------
    # 3. FRAMEWORKS & LIBRARIES
    # -------------------------------------------------------------
    if "__next_data__" in html_lower or "_next/static" in html_lower:
        tech["framework"].append("Next.js")
        tech["framework"].append("React")
    elif "react" in html_lower or "_reactroot" in html_lower:
        tech["framework"].append("React")
        
    if "__nuxt__" in html_lower:
        tech["framework"].append("Nuxt")
        tech["framework"].append("Vue.js")
    elif "vue" in html_lower or "data-v-" in html_lower:
        tech["framework"].append("Vue.js")

    if "angular" in html_lower or "ng-version" in html_lower:
        tech["framework"].append("Angular")
    if "svelte" in html_lower:
        tech["framework"].append("Svelte")
    if "alpine" in html_lower or "x-data=" in html_lower:
        tech["framework"].append("Alpine.js")
    if "jquery" in html_lower or "jquery.min.js" in html_lower:
        tech["framework"].append("jQuery")
    if "tailwind" in html_lower:
        tech["framework"].append("Tailwind CSS")
    if "bootstrap" in html_lower:
        tech["framework"].append("Bootstrap")

    if not tech["framework"]:
        tech["framework"].append("HTML5 / Vanilla JS")

    # -------------------------------------------------------------
    # 4. ANALYTICS
    # -------------------------------------------------------------
    if "gtag('config', 'g-" in html_lower or "googletagmanager.com/gtag/js?id=g-" in html_lower or "analytics.js" in html_lower:
        tech["analytics"].append("Google Analytics 4 (GA4)")
    if "ua-" in html_lower or "_gaq" in html_lower:
        tech["analytics"].append("Universal Analytics (legacy)")
    if "plausible" in html_lower:
        tech["analytics"].append("Plausible Analytics")
    if "fathom" in html_lower:
        tech["analytics"].append("Fathom Analytics")
    if "matomo" in html_lower or "piwik" in html_lower:
        tech["analytics"].append("Matomo")
    if "hotjar" in html_lower or "static.hotjar.com" in html_lower:
        tech["analytics"].append("Hotjar")
    if "clarity.ms" in html_lower:
        tech["analytics"].append("Microsoft Clarity")
    if "mixpanel" in html_lower:
        tech["analytics"].append("Mixpanel")

    if not tech["analytics"]:
        tech["analytics"].append("None detected")

    # -------------------------------------------------------------
    # 5. TAG MANAGER
    # -------------------------------------------------------------
    if "googletagmanager.com/gtm.js" in html_lower or "gtm-" in html_lower:
        tech["tag_manager"].append("Google Tag Manager")
    if "adobe" in html_lower and "satellite" in html_lower:
        tech["tag_manager"].append("Adobe Experience Platform Launch")
    if "tealium" in html_lower:
        tech["tag_manager"].append("Tealium")

    if not tech["tag_manager"]:
        tech["tag_manager"].append("None detected")

    # -------------------------------------------------------------
    # 6. MARKETING TRACKERS & PIXELS
    # -------------------------------------------------------------
    if "connect.facebook.net" in html_lower or "fbq(" in html_lower:
        tech["marketing_trackers"].append("Meta Pixel (Facebook)")
    if "analytics.tiktok.com" in html_lower or "ttq" in html_lower:
        tech["marketing_trackers"].append("TikTok Pixel")
    if "googleadservices.com" in html_lower or "gtag('config', 'aw-" in html_lower or "doubleclick.net" in html_lower:
        tech["marketing_trackers"].append("Google Ads / DoubleClick")
    if "static.klaviyo.com" in html_lower or "_learnq" in html_lower:
        tech["marketing_trackers"].append("Klaviyo")
    if "pintrk" in html_lower:
        tech["marketing_trackers"].append("Pinterest Tag")
    if "static.ads-twitter.com" in html_lower or "twq(" in html_lower:
        tech["marketing_trackers"].append("Twitter/X Pixel")
    if "criteo" in html_lower:
        tech["marketing_trackers"].append("Criteo")

    if not tech["marketing_trackers"]:
        tech["marketing_trackers"].append("None detected")

    # De-duplicate entries preserving order
    for k in tech:
        seen = set()
        deduped = []
        for item in tech[k]:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        tech[k] = deduped

    return tech

async def detect_technologies_for_site(url: str, html: str = "", headers: Optional[Dict[str, str]] = None) -> Dict[str, List[str]]:
    """
    Asynchronously detect technologies for a site, fetching the URL if html/headers are not provided.
    """
    if html and headers:
        return detect_technologies(html, headers, url)
        
    import httpx
    fetched_html = html
    fetched_headers = headers or {}
    
    if not fetched_html and url:
        try:
            req_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=6.0) as client:
                resp = await client.get(url, headers=req_headers)
                fetched_html = resp.text
                fetched_headers = dict(resp.headers)
        except Exception:
            pass
            
    return detect_technologies(fetched_html, fetched_headers, url)
