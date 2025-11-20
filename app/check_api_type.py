# Test për të parë API response raw
import requests
import json

API_KEY = 'f7b40af0-9689-4872-8d59-4779f7961175'
BASE = 'https://efaktura.mfin.gov.rs'

headers = {
    'ApiKey': API_KEY,
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

print("=" * 80)
print("DEBUG - Duke kontrolluar API response")
print("=" * 80)

# Test 1: POST /api/publicApi/purchase-invoice/ids
print("\n1. POST /api/publicApi/purchase-invoice/ids")
print("   (Faktura që ti ke MARRË - purchase invoices)")

url = f'{BASE}/api/publicApi/purchase-invoice/ids'
payload = {
    'dateFrom': '2024-01-01',
    'dateTo': '2025-11-18'
}

print(f"\n   URL: {url}")
print(f"   Payload: {json.dumps(payload, indent=2)}")

try:
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"\n   Status: {r.status_code}")
    print(f"   Response: {r.text[:500]}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"\n   ✓ Tip: {type(data)}")
        if isinstance(data, list):
            print(f"   ✓ Numri i fakturave (PURCHASE): {len(data)}")
            if data:
                print(f"   ✓ Shembull IDs: {data[:5]}")
        else:
            print(f"   ✓ Data: {data}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Try sales-invoice (faktura që ti ke DËRGUAR)
print("\n" + "=" * 80)
print("2. POST /api/publicApi/sales-invoice/ids")
print("   (Faktura që ti ke DËRGUAR - sales invoices)")

url2 = f'{BASE}/api/publicApi/sales-invoice/ids'

print(f"\n   URL: {url2}")
print(f"   Payload: {json.dumps(payload, indent=2)}")

try:
    r2 = requests.post(url2, json=payload, headers=headers, timeout=30)
    print(f"\n   Status: {r2.status_code}")
    print(f"   Response: {r2.text[:500]}")
    
    if r2.status_code == 200:
        data2 = r2.json()
        print(f"\n   ✓ Tip: {type(data2)}")
        if isinstance(data2, list):
            print(f"   ✓ Numri i fakturave (SALES): {len(data2)}")
            if data2:
                print(f"   ✓ Shembull IDs: {data2[:5]}")
        else:
            print(f"   ✓ Data: {data2}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 80)
