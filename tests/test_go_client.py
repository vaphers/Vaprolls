import asyncio
import os
import sys
import subprocess
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from crawler.go_client import GoCrawlerClient

async def run_test():
    crawler_exe = os.path.abspath("go-crawler/bin/crawler.exe")
    if not os.path.exists(crawler_exe):
        print(f"Error: {crawler_exe} not found. Run go build first.")
        return False

    test_port = 50055
    data_dir = os.path.abspath("data/test_crawler")
    print(f"Starting Go crawler server on port {test_port}...")
    
    proc = subprocess.Popen([crawler_exe, f"--port={test_port}", f"--data-dir={data_dir}"])
    try:
        client = GoCrawlerClient(host="127.0.0.1", port=test_port)
        
        # 1. Wait for server to become ready
        ready = False
        for attempt in range(10):
            if await client.is_available(timeout_sec=0.5):
                ready = True
                print("Go crawler server is READY!")
                break
            await asyncio.sleep(0.3)
            
        if not ready:
            print("Failed to connect to Go crawler server.")
            return False

        # 2. Start a test crawl
        audit_id = f"test-audit-{int(time.time())}"
        print(f"Starting test crawl on https://example.com with audit_id: {audit_id}...")
        req = {
            "audit_id": audit_id,
            "start_url": "https://example.com",
            "max_pages": 2,
            "concurrency": 2,
            "max_per_host": 2,
            "host_delay_ms": 100,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestCrawler/1.0",
            "crawl_mode": "spider",
        }

        events_received = []
        pages_received = []

        async for event in client.start_crawl(req):
            events_received.append(event.type)
            if event.type == "page_result" and event.page:
                pages_received.append(event.page)
                print(f"  [Page Received] URL: {event.page.url}, Status: {event.page.status_code}, Title: {event.page.title}")
            elif event.type == "progress" and event.progress:
                p = event.progress
                print(f"  [Progress] Crawled: {p.pages_crawled}, Queue: {p.queue_size}, Speed: {p.pages_per_sec:.1f} p/s")
            elif event.type == "completed":
                print(f"  [Complete] {event.message}")

        print(f"\nTotal events: {len(events_received)}")
        print(f"Total pages received: {len(pages_received)}")

        assert len(pages_received) >= 1, "Expected at least 1 page to be crawled"
        assert pages_received[0].status_code == 200, f"Expected status 200, got {pages_received[0].status_code}"
        assert "Example Domain" in (pages_received[0].title or ""), f"Expected 'Example Domain' in title, got: {pages_received[0].title}"
        
        print("\nAll integration assertions passed successfully!")
        await client.close()
        return True

    finally:
        print("Terminating Go crawler test server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    success = asyncio.run(run_test())
    if not success:
        exit(1)
