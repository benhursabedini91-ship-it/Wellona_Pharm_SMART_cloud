# Check pagination dhe total count
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
print("CHECK - A ka më shumë faktura? (Pagination)")
print("=" * 80)

# Try different date ranges to see if there's more
test_ranges = [
    ('2024-01-01', '2024-03-31', 'Q1 2024'),
    ('2024-04-01', '2024-06-30', 'Q2 2024'),
    ('2024-07-01', '2024-09-30', 'Q3 2024'),
    ('2024-10-01', '2024-12-31', 'Q4 2024'),
    ('2025-01-01', '2025-11-18', '2025 YTD'),
]

url = f'{BASE}/api/publicApi/purchase-invoice/ids'
total_all = 0

for date_from, date_to, label in test_ranges:
    payload = {
        'dateFrom': date_from,
        'dateTo': date_to
    }
    
    print(f"\n📅 {label} ({date_from} deri {date_to})")
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            ids = data.get('PurchaseInvoiceIds', [])
            count = len(ids)
            total_all += count
            print(f"   ✓ {count} faktura")
            if count > 0:
                print(f"   First ID: {ids[0]}, Last ID: {ids[-1]}")
        else:
            print(f"   ✗ Error: {r.status_code}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")

print("\n" + "=" * 80)
print(f"📊 TOTAL: {total_all} faktura në të gjitha periudhat")
print("=" * 80)

# Try with pagination parameters if supported
print("\n🔍 Duke testuar pagination parameters...")

payload_with_page = {
    'dateFrom': '2024-01-01',
    'dateTo': '2025-11-18',
    'page': 0,
    'size': 100
}

try:
    r = requests.post(url, json=payload_with_page, headers=headers, timeout=30)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   Response keys: {list(data.keys())}")
        ids = data.get('PurchaseInvoiceIds', [])
        print(f"   Count me pagination: {len(ids)}")
    else:
        print(f"   Response: {r.text[:200]}")
except Exception as e:
    print(f"   Exception: {e}")

print("\n" + "=" * 80)
