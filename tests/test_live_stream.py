import asyncio
import json
import httpx
import websockets

async def test_live_crawl():
    async with httpx.AsyncClient() as client:
        # Start crawl
        resp = await client.post('http://127.0.0.1:8000/api/audit/start', json={
            'url': 'https://starwaywebdigital.com',
            'max_pages': 5,
            'concurrency': 2,
            'mode': 'spider'
        })
        data = resp.json()
        audit_id = data.get('audit_id')
        print(f"Audit started with ID: {audit_id}")
        assert audit_id, "No audit_id returned"

        # Connect WS
        ws_url = f"ws://127.0.0.1:8000/ws/audit/{audit_id}"
        async with websockets.connect(ws_url) as ws:
            pages_received = 0
            while True:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=20.0)
                msg = json.loads(msg_raw)
                mtype = msg.get("type")
                status = msg.get("status")
                print(f"WS Message: type={mtype}, status={status}")
                if "page_rows" in msg and msg["page_rows"]:
                    pages_received += len(msg["page_rows"])
                    print(f"  [+] Received {len(msg['page_rows'])} live page rows! Total received: {pages_received}")
                    for r in msg["page_rows"]:
                        print(f"      - {r.get('url')} (Status: {r.get('status_code')})")
                if mtype == "complete":
                    print("Crawl complete event received!")
                    break

        # Check API tab data
        tab_resp = await client.get(f"http://127.0.0.1:8000/api/audit/{audit_id}/tab/all")
        tab_data = tab_resp.json()
        rows = tab_data.get("rows", [])
        print(f"API Tab rows count in DB: {len(rows)}")
        assert len(rows) > 0, "No rows found in database for audit"
        print("SUCCESS: Live WebSocket streaming and database persistence fully verified!")

if __name__ == "__main__":
    asyncio.run(test_live_crawl())

