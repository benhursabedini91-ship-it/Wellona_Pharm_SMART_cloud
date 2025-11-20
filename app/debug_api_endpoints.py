# Debug script - kontroll direct i API endpoints
import requests

API_KEY = 'f7b40af0-9689-4872-8d59-4779f7961175'
BASE = 'https://efaktura.mfin.gov.rs'

headers = {
    'ApiKey': API_KEY,
    'Accept': '*/*'
}

print("=" * 80)
print("DEBUG - eFaktura API Endpoints")
print("=" * 80)

# Test 1: Try to get swagger/openapi spec
print("\n1. Duke marrë API spec...")
try:
    r = requests.get(f'{BASE}/swagger/v1/swagger.json', headers=headers, timeout=10)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        import json
        spec = r.json()
        print("   ✓ API spec OK")
        print(f"   Paths: {list(spec.get('paths', {}).keys())[:10]}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Try different list endpoint variations
print("\n2. Duke testuar endpoint-ë të ndryshëm për listim...")

test_urls = [
    # Try with different param names based on swagger screenshot
    '/api/publicApi/purchase-invoice/ids?dateFrom=2025-11-01&dateTo=2025-11-18',
    '/api/publicApi/purchase-invoice?from=2025-11-01&to=2025-11-18',
    '/api/publicApi/purchase-invoice/list?dateFrom=2025-11-01&dateTo=2025-11-18',
    '/api/publicApi/purchase-invoice?startDate=2025-11-01&endDate=2025-11-18',
    # Maybe it needs pagination
    '/api/publicApi/purchase-invoice?dateFrom=2025-11-01&dateTo=2025-11-18&page=0&size=10',
]

for path in test_urls:
    url = BASE + path
    print(f"\n   Testing: {path[:60]}...")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   ✓ SUCCESS!")
            data = r.json()
            print(f"   Response type: {type(data)}")
            if isinstance(data, list):
                print(f"   Count: {len(data)}")
                if data:
                    print(f"   First item keys: {list(data[0].keys())}")
            elif isinstance(data, dict):
                print(f"   Keys: {list(data.keys())}")
            break
        elif r.status_code == 404:
            print(f"   ✗ Not found")
        else:
            print(f"   ✗ Error: {r.text[:100]}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")

print("\n" + "=" * 80)
