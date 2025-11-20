"""
Test ALL eFaktura API endpoints to find pagination parameters.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import requests
from efaktura_client import make_session
from datetime import date, timedelta

def test_pagination_params():
    """Test different pagination parameters."""
    s = make_session()
    
    date_from = date(2025, 9, 1)
    date_to = date(2025, 11, 18)
    
    url = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/ids"
    
    print("=" * 80)
    print("  TESTIMI I PAGINATION PARAMETRAVE")
    print("=" * 80)
    
    # Test 1: Default (no pagination)
    print("\n1. DEFAULT (pa parametra):")
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat()
    }
    r = s.post(url, json=payload, timeout=60)
    if r.status_code == 200:
        data = r.json()
        ids = data.get('PurchaseInvoiceIds', [])
        print(f"   ✓ {len(ids)} faktura")
    else:
        print(f"   ✗ Error: {r.status_code}")
    
    # Test 2: With page/pageSize
    print("\n2. ME page=1, pageSize=100:")
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "page": 1,
        "pageSize": 100
    }
    r = s.post(url, json=payload, timeout=60)
    if r.status_code == 200:
        data = r.json()
        ids = data.get('PurchaseInvoiceIds', [])
        print(f"   ✓ {len(ids)} faktura")
        print(f"   Response keys: {list(data.keys())}")
    else:
        print(f"   ✗ Error: {r.status_code}")
    
    # Test 3: With skip/take
    print("\n3. ME skip=0, take=100:")
    
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "skip": 0,
        "take": 100
    }
    r = s.post(url, json=payload, timeout=60)
    if r.status_code == 200:
        data = r.json()
        ids = data.get('PurchaseInvoiceIds', [])
        print(f"   ✓ {len(ids)} faktura")
    else:
        print(f"   ✗ Error: {r.status_code}")
    
    # Test 4: With offset/limit
    print("\n4. ME offset=0, limit=100:")
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "offset": 0,
        "limit": 100
    }
    r = s.post(url, json=payload, timeout=60)
    if r.status_code == 200:
        data = r.json()
        ids = data.get('PurchaseInvoiceIds', [])
        print(f"   ✓ {len(ids)} faktura")
    else:
        print(f"   ✗ Error: {r.status_code}")
    
    # Test 5: Check response headers for pagination hints
    print("\n5. RESPONSE HEADERS:")
    r = s.post(url, json={
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat()
    }, timeout=60)
    
    for key, value in r.headers.items():
        if any(hint in key.lower() for hint in ['page', 'total', 'count', 'link', 'next']):
            print(f"   {key}: {value}")
    
    # Test 6: Very narrow date range (1 day)
    print("\n6. DITA E VETME (2025-11-15):")
    payload = {
        "dateFrom": "2025-11-15",
        "dateTo": "2025-11-15"
    }
    r = s.post(url, json=payload, timeout=60)
    if r.status_code == 200:
        data = r.json()
        ids = data.get('PurchaseInvoiceIds', [])
        print(f"   ✓ {len(ids)} faktura")
        if ids:
            print(f"   First ID: {ids[0]}")
            print(f"   Last ID: {ids[-1]}")
    
    print("\n" + "=" * 80)
    print("PËRFUNDIM: Nëse të gjitha kthejnë 50, NUK KA PAGINATION!")
    print("=" * 80)

if __name__ == "__main__":
    test_pagination_params()
