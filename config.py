import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

USER_AGENT_PRESETS = {
    'default': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'chrome_desktop': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'chrome_mobile': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
    'googlebot_smartphone': 'Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'googlebot_desktop': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'bingbot': 'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
    'custom_crawler': 'SEOAuditor/2.0'
}

@dataclass
class Config:
    CRAWL_CONCURRENCY: int = 15
    CRAWL_DELAY: float = 0.0
    MAX_PAGES: int = 5000
    REQUEST_TIMEOUT: int = 10
    USER_AGENT: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    DB_PATH: str = 'data/audits.db'
    LIGHTHOUSE_PATH: str = 'npx lighthouse'
    LIGHTHOUSE_ENABLED: bool = False  # Disabled by default for fast audits; use CrUX API or custom metrics
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv('GEMINI_API_KEY', ''))
    REPORTS_DIR: str = 'reports_output/'
    JS_RENDER_ENABLED: bool = False
    RESPECT_ROBOTS_TXT: bool = True
    FOLLOW_REDIRECTS: bool = True
    MAX_REDIRECT_CHAIN: int = 10
    MOBILE_VIEWPORT: Dict[str, int] = field(default_factory=lambda: {'width': 375, 'height': 667})
    DESKTOP_VIEWPORT: Dict[str, int] = field(default_factory=lambda: {'width': 1920, 'height': 1080})

    # Enterprise Scope & Crawl Mode Settings
    CRAWL_MODE: str = 'spider'  # 'spider', 'list', 'sitemap'
    URLS_LIST: List[str] = field(default_factory=list)
    INCLUDE_REGEX: List[str] = field(default_factory=list)
    EXCLUDE_REGEX: List[str] = field(default_factory=list)
    MAX_CRAWL_DEPTH: Optional[int] = None
    
    # Staging & Bot Emulation
    USER_AGENT_PRESET: str = 'default'
    HTTP_AUTH: Optional[Dict[str, str]] = None  # {'username': '...', 'password': '...'}
    CUSTOM_HEADERS: Dict[str, str] = field(default_factory=dict)
    PROXY: Optional[str] = None  # 'http://proxy:8080' or 'socks5://proxy:1080'
    
    # Custom Extraction & Search Rules
    CUSTOM_EXTRACTIONS: List[Dict[str, str]] = field(default_factory=list)
    # e.g. [{'name': 'Price', 'type': 'css', 'selector': '.price'}]
    CUSTOM_SEARCHES: List[Dict[str, str]] = field(default_factory=list)
    # e.g. [{'name': 'Missing GA4', 'type': 'does_not_contain', 'query': 'G-XXXXXXXX'}]

_config_instance = None

def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
