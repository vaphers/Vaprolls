import asyncio
import os
import re
import hashlib
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class JSRenderer:
    """Headless Chromium rendering engine using Playwright for full client-side JavaScript execution."""

    def __init__(self, concurrency: int = 4, timeout_ms: int = 15000):
        self.concurrency = concurrency
        self.timeout_ms = timeout_ms
        self.playwright = None
        self.browser = None
        self._lock = asyncio.Lock()
        self.is_initialized = False

    async def initialize(self):
        if self.is_initialized:
            return
        async with self._lock:
            if self.is_initialized:
                return
            try:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-gpu",
                        "--blink-settings=imagesEnabled=true"
                    ]
                )
                self.is_initialized = True
                logger.info("Playwright Chromium Headless Renderer initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Playwright Chromium Renderer: {e}")
                self.is_initialized = False

    async def close(self):
        async with self._lock:
            if self.browser:
                try:
                    await self.browser.close()
                except Exception:
                    pass
                self.browser = None
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception:
                    pass
                self.playwright = None
            self.is_initialized = False

    async def render_url(
        self,
        url: str,
        user_agent: Optional[str] = None,
        audit_id: Optional[str] = None,
        take_screenshot: bool = True
    ) -> Dict[str, Any]:
        """Renders URL in headless Chromium, executing client-side JS and collecting DOM metrics."""
        if not self.is_initialized:
            await self.initialize()

        if not self.browser:
            return {}

        context = None
        page = None
        js_errors = []
        js_warnings = []
        js_logs = []

        try:
            ua = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            context = await self.browser.new_context(
                user_agent=ua,
                viewport={"width": 1366, "height": 768},
                ignore_https_errors=True
            )
            page = await context.new_page()

            # Listen to console messages and page errors
            def on_console(msg):
                if msg.type == "error":
                    js_errors.append(msg.text[:200])
                elif msg.type == "warning":
                    js_warnings.append(msg.text[:200])
                elif msg.type in ("info", "log"):
                    js_logs.append(msg.text[:200])

            page.on("console", on_console)
            page.on("pageerror", lambda err: js_errors.append(str(err)[:200]))

            resp = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            # Give short breather for JS frameworks (React/Vue/Next.js) to hydrate
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass

            rendered_html = await page.content()
            status_code = resp.status if resp else 200

            # Extract rendered metadata from live DOM
            title = await page.title()
            
            # Use BeautifulSoup to parse rendered DOM
            soup = BeautifulSoup(rendered_html, 'html.parser')
            
            meta_desc_tag = soup.find('meta', attrs={'name': lambda x: x and x.lower() == 'description'})
            meta_description = meta_desc_tag['content'].strip() if (meta_desc_tag and meta_desc_tag.get('content')) else ''

            h1_tag = soup.find('h1')
            h1 = h1_tag.get_text(strip=True) if h1_tag else ''

            canon_tag = soup.find('link', rel=lambda x: x and 'canonical' in [r.lower() for r in (x if isinstance(x, list) else [x])])
            canonical_url = canon_tag['href'].strip() if (canon_tag and canon_tag.get('href')) else ''

            # Word count
            body = soup.find('body')
            body_text = body.get_text(" ", strip=True) if body else ""
            words = re.findall(r'\b\w+\b', body_text)
            rendered_word_count = len(words)

            # Rendered Links
            rendered_links = []
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    rendered_links.append({
                        "url": href,
                        "anchor": a.get_text(strip=True),
                        "rel": a.get('rel', [])
                    })

            # Optional screenshot
            screenshot_path = ""
            if take_screenshot and audit_id:
                try:
                    screenshots_dir = os.path.join(os.getcwd(), "data", "screenshots", audit_id)
                    os.makedirs(screenshots_dir, exist_ok=True)
                    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
                    shot_file = os.path.join(screenshots_dir, f"{url_hash}.jpg")
                    await page.screenshot(path=shot_file, type="jpeg", quality=65)
                    screenshot_path = f"/api/proxy/screenshot/{audit_id}/{url_hash}.jpg"
                except Exception as ex_shot:
                    logger.debug(f"Screenshot capture failed for {url}: {ex_shot}")

            return {
                "url": url,
                "status_code": status_code,
                "rendered_html": rendered_html,
                "rendered_title": title,
                "rendered_meta_description": meta_description,
                "rendered_h1": h1,
                "rendered_canonical": canonical_url,
                "rendered_word_count": rendered_word_count,
                "js_errors_count": len(js_errors),
                "js_warnings_count": len(js_warnings),
                "js_errors": js_errors[:10],
                "js_warnings": js_warnings[:10],
                "rendered_links": rendered_links,
                "screenshot_url": screenshot_path
            }

        except Exception as e:
            logger.warning(f"Error rendering {url} with Playwright: {e}")
            return {
                "url": url,
                "error": str(e),
                "js_errors_count": len(js_errors) + 1,
                "js_errors": js_errors + [str(e)]
            }
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

