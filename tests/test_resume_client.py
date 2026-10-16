import asyncio
import os
import sys
import subprocess
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from crawler.go_client import GoCrawlerClient

async def run_resume_test():
    crawler_exe = os.path.abspath("go-crawler/bin/crawler.exe")
    test_port = 50056
    data_dir = os.path.abspath("data/test_resume_crawler")
    
    proc = subprocess.Popen([crawler_exe, f"--port={test_port}", f"--data-dir={data_dir}"])
    try:
        client = GoCrawlerClient(host="127.0.0.1", port=test_port)
        
        # 1. Wait for server ready
        for _ in range(10):
            if await client.is_available(timeout_sec=0.5):
                break
            await asyncio.sleep(0.3)
            
        audit_id = f"test-resume-{int(time.time())}"
        
        # 2. Start initial crawl
        req = {
            "audit_id": audit_id,
            "start_url": "https://example.com",
            "max_pages": 1,
            "concurrency": 1,
            "max_per_host": 1,
            "host_delay_ms": 100,
            "user_agent": "Mozilla/5.0 TestResume/1.0",
            "crawl_mode": "spider",
        }

        async for event in client.start_crawl(req):
            if event.type == "page_result":
                print(f"StartCrawl page: {event.page.url}")
                
        # 3. Call ResumeCrawl on the same audit_id
        print(f"Calling ResumeCrawl on {audit_id}...")
        resumed_events = []
        async for event in client.resume_crawl(audit_id=audit_id):
            resumed_events.append(event.type)
            if event.type == "completed":
                print(f"ResumeCrawl completed: {event.message}")

        print(f"Resume events received: {resumed_events}")
        assert "completed" in resumed_events, "Expected completed event during resume"
        print("ResumeCrawl test passed successfully!")
        
        await client.close()
        return True
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    if not asyncio.run(run_resume_test()):
        sys.exit(1)
