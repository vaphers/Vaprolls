import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)

def test_react_spa():
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert 'root' in res.text, "Root element missing"
    assert 'VAPLERS' in res.text, "Title missing"
    print("React SPA index.html successfully served from /!")

    import re
    match = re.search(r'src="(/assets/index-[^"]+\.js)"', res.text)
    assert match, "Asset script tag not found in index.html"
    asset_path = match.group(1)

    res_asset = client.get(asset_path)
    assert res_asset.status_code == 200, f"Asset status: {res_asset.status_code}"
    print(f"React JS bundle ({asset_path}) successfully served (status 200, size: {len(res_asset.content)} bytes)!")

if __name__ == '__main__':
    test_react_spa()
