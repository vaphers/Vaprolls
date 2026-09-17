import httpx
import logging
import gzip
from typing import List, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

@dataclass
class SitemapURL:
    url: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None
    sitemap_url: Optional[str] = None

class SitemapParser:
    """
    Fetches and parses XML sitemaps, including nested sitemap indexes and gzipped sitemaps.
    """
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client
        self.urls: List[SitemapURL] = []
        self.errors: List[str] = []

    async def fetch_and_parse(self, sitemap_url: str) -> List[SitemapURL]:
        """Fetch and parse a sitemap (or sitemap index). Returns list of SitemapURL."""
        should_close = False
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
            should_close = True

        try:
            await self._process_sitemap(sitemap_url)
        finally:
            if should_close and self.client:
                await self.client.aclose()
                self.client = None
                
        return self.urls

    async def _process_sitemap(self, url: str) -> None:
        """Internal method to process a sitemap URL recursively."""
        try:
            if not self.client:
                raise ValueError("HTTP client not initialized.")
                
            response = await self.client.get(url)
            response.raise_for_status()
            
            content = response.content
            if url.endswith('.gz'):
                try:
                    content = gzip.decompress(content)
                except Exception as e:
                    logger.error(f"Failed to decompress gzipped sitemap {url}: {e}")
                    self.errors.append(f"Decompression error for {url}: {str(e)}")
                    return

            soup = BeautifulSoup(content, 'lxml-xml')
            
            # Check if it's a sitemap index
            if soup.find('sitemapindex'):
                sitemaps = soup.find_all('sitemap')
                for sm in sitemaps:
                    loc = sm.find('loc')
                    if loc and loc.text:
                        next_url = loc.text.strip()
                        await self._process_sitemap(next_url)
            
            # Check if it's a urlset (regular sitemap)
            elif soup.find('urlset'):
                urls = soup.find_all('url')
                for u in urls:
                    loc_tag = u.find('loc')
                    if not loc_tag or not loc_tag.text:
                        continue
                    
                    loc = loc_tag.text.strip()
                    lastmod_tag = u.find('lastmod')
                    lastmod = lastmod_tag.text.strip() if lastmod_tag else None
                    
                    changefreq_tag = u.find('changefreq')
                    changefreq = changefreq_tag.text.strip() if changefreq_tag else None
                    
                    priority_tag = u.find('priority')
                    priority = None
                    if priority_tag and priority_tag.text:
                        try:
                            priority = float(priority_tag.text.strip())
                        except ValueError:
                            pass
                            
                    self.urls.append(SitemapURL(
                        url=loc,
                        lastmod=lastmod,
                        changefreq=changefreq,
                        priority=priority,
                        sitemap_url=url
                    ))
            else:
                self.errors.append(f"Invalid XML format (neither sitemapindex nor urlset found) in {url}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching sitemap {url}: {e}")
            self.errors.append(f"HTTP error for {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing sitemap {url}: {e}")
            self.errors.append(f"Error for {url}: {str(e)}")

    def get_all_urls(self) -> List[SitemapURL]:
        """Return all parsed URLs."""
        return self.urls
