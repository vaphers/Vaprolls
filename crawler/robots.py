import urllib.robotparser
import httpx
from urllib.parse import urlparse, urljoin
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class RobotsParser:
    """
    Fetches and parses robots.txt from a given domain.
    """
    def __init__(self, domain_url: str):
        self.domain_url = domain_url
        parsed = urlparse(domain_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.robots_url = urljoin(self.base_url, "/robots.txt")
        self.parser = urllib.robotparser.RobotFileParser()
        self.parser.set_url(self.robots_url)
        self.sitemaps: List[str] = []
        self.fetched = False

    async def fetch_and_parse(self, client: Optional[httpx.AsyncClient] = None) -> None:
        """Fetches and parses the robots.txt file."""
        if self.fetched:
            return

        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
            should_close = True

        try:
            response = await client.get(self.robots_url)
            if response.status_code == 200:
                lines = response.text.splitlines()
                self.parser.parse(lines)
                
                # Extract sitemaps manually since robotparser might not store all of them or we want them explicit
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith("sitemap:"):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            sitemap_url = parts[1].strip()
                            self.sitemaps.append(sitemap_url)
            else:
                logger.warning(f"robots.txt not found or error (status {response.status_code}) for {self.robots_url}. Assuming allow all.")
                self.parser.allow_all = True

        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {self.robots_url}: {e}. Assuming allow all.")
            self.parser.allow_all = True
        finally:
            if should_close:
                await client.aclose()
            self.fetched = True

    def is_allowed(self, url: str, user_agent: str = '*') -> bool:
        """Check if a URL is allowed for the given user agent."""
        if not self.fetched:
            logger.warning("RobotsParser.fetch_and_parse() should be called before is_allowed()")
            
        # If allow_all is set manually (e.g. on error) or the parser is empty
        if getattr(self.parser, 'allow_all', False):
            return True
            
        return self.parser.can_fetch(user_agent, url)

    def get_crawl_delay(self, user_agent: str = '*') -> Optional[float]:
        """Get the crawl delay for the given user agent."""
        if not self.fetched:
            logger.warning("RobotsParser.fetch_and_parse() should be called before get_crawl_delay()")
        
        try:
            delay = self.parser.crawl_delay(user_agent)
            return float(delay) if delay is not None else None
        except Exception:
            return None

    def get_sitemaps(self) -> List[str]:
        """Get a list of sitemap URLs found in robots.txt."""
        if not self.fetched:
            logger.warning("RobotsParser.fetch_and_parse() should be called before get_sitemaps()")
        
        # urllib.robotparser also stores sitemaps in some python versions:
        parser_sitemaps = getattr(self.parser, 'sitemaps', None)
        if parser_sitemaps:
            for sm in parser_sitemaps:
                if sm not in self.sitemaps:
                    self.sitemaps.append(sm)
                    
        return self.sitemaps
