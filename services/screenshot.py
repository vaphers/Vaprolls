import os
import asyncio
import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

CHROME_CANDIDATE_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]

def find_browser_executable() -> Optional[str]:
    for path in CHROME_CANDIDATE_PATHS:
        if os.path.exists(path):
            return path
    return None

async def capture_screenshots(url: str, audit_id: str, output_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Captures desktop (1280x800) and mobile (390x844) screenshots using headless Chrome.
    Returns relative URLs or filenames: (desktop_rel_path, mobile_rel_path).
    """
    browser = find_browser_executable()
    if not browser:
        logger.warning("No Chrome or Edge browser executable found for screenshots.")
        return None, None

    os.makedirs(output_dir, exist_ok=True)
    desktop_filename = f"{audit_id}_desktop.png"
    mobile_filename = f"{audit_id}_mobile.png"
    
    desktop_abs = os.path.join(output_dir, desktop_filename)
    mobile_abs = os.path.join(output_dir, mobile_filename)

    def _take_screenshot(target_file: str, width: int, height: int, mobile_ua: bool = False):
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            f"--window-size={width},{height}",
            f"--screenshot={target_file}",
        ]
        if mobile_ua:
            cmd.append("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1")
        cmd.append(url)
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        except Exception as e:
            logger.error(f"Error capturing screenshot for {url}: {e}")

    try:
        # Run desktop screenshot
        await asyncio.to_thread(_take_screenshot, desktop_abs, 1280, 800, False)
        # Run mobile screenshot
        await asyncio.to_thread(_take_screenshot, mobile_abs, 390, 844, True)
    except Exception as e:
        logger.error(f"Failed to capture screenshots for audit {audit_id}: {e}")

    desktop_res = f"/static/screenshots/{desktop_filename}" if os.path.exists(desktop_abs) else None
    mobile_res = f"/static/screenshots/{mobile_filename}" if os.path.exists(mobile_abs) else None
    
    return desktop_res, mobile_res
