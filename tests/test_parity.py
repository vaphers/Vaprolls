import re
import hashlib
from urllib.parse import urlparse, urljoin, urldefrag, parse_qs, urlencode
import subprocess
import json

def python_normalize_url(url: str, base_url: str) -> str:
    absolute = urljoin(base_url, url)
    absolute, _ = urldefrag(absolute)
    
    parsed = urlparse(absolute)
    
    # remove common tracking parameters
    query_params = parse_qs(parsed.query)
    tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid'}
    clean_params = {k: v for k, v in query_params.items() if k not in tracking_params}
    
    clean_query = urlencode(clean_params, doseq=True)
    
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
        
    norm = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    if clean_query:
        norm += f"?{clean_query}"
        
    return norm

def python_compute_simhash(text: str) -> int:
    if not text:
        return 0
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    if not words:
        return 0
    v = [0] * 64
    for word in words:
        h = int(hashlib.md5(word.encode('utf-8')).hexdigest()[:16], 16)
        for i in range(64):
            bit = (h >> i) & 1
            if bit:
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint

def main():
    test_urls = [
        ("/blog/post-1/", "https://example.com"),
        ("page.html?utm_source=google&id=42#reviews", "https://example.com/section/"),
        ("https://EXAMPLE.COM/about/?fbclid=XYZ&ref=abc", "https://example.com"),
        ("/", "https://example.com/"),
        ("/products/item?gclid=123", "https://example.com/catalog/"),
    ]

    print("Checking Python normalizer baseline...")
    for raw, base in test_urls:
        norm = python_normalize_url(raw, base)
        print(f"  {raw} + {base} -> {norm}")

    test_text = "The quick brown fox jumps over the lazy dog and explores search engine optimization techniques."
    py_simhash = python_compute_simhash(test_text)
    py_simhash_hex = f"{py_simhash:016x}"
    print(f"\nPython SimHash for test text: {py_simhash_hex}")

    print("\nAll baseline tests ready!")

if __name__ == "__main__":
    main()
