"""
Test advanced filtering with RestrictionItem to bypass 50-limit.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import make_session
from datetime import date

def test_with_filters():
    """Test filtering by supplier to get more invoices."""
    s = make_session()
    
    url = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/ids"
    
    date_from = date(2024, 1, 1)
    date_to = date(2025, 11, 18)
    
    print("=" * 80)
    print("  TESTIMI I FILTRAVE (RestrictionItem)")
    print("=" * 80)
    
    # Test 1: No filter (baseline)
    print("\n1. PA FILTRA:")
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat()
    }
    
    try:
        r = s.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            ids = r.json().get('PurchaseInvoiceIds', [])
            print(f"   ✓ {len(ids)} faktura")
        else:
            print(f"   ✗ {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"   ✗ {e}")
    
    # Test 2: Filter by sender (PHOENIX)
    print("\n2. FILTRO: Invoice_Sender_Like = 'PHOENIX':")
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "restrictions": [
            {
                "field": "Invoice_Sender_Like",
                "values": ["PHOENIX"]
            }
        ]
    }
    
    try:
        r = s.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            ids = r.json().get('PurchaseInvoiceIds', [])
            print(f"   ✓ {len(ids)} faktura nga PHOENIX")
        else:
            print(f"   ✗ {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"   ✗ {e}")
    
    # Test 3: Filter by sender (VEGA)
    print("\n3. FILTRO: Invoice_Sender_Like = 'VEGA':")
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "restrictions": [
            {
                "field": "Invoice_Sender_Like",
                "values": ["VEGA"]
            }
        ]
    }
    
    try:
        r = s.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            ids = r.json().get('PurchaseInvoiceIds', [])
            print(f"   ✓ {len(ids)} faktura nga VEGA")
        else:
            print(f"   ✗ {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"   ✗ {e}")
    
    # Test 4: Filter by status
    print("\n4. FILTRO: Invoice_Status = 'New':")
    payload = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "restrictions": [
            {
                "field": "Invoice_Status",
                "values": ["New"]
            }
        ]
    }
    
    try:
        r = s.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            ids = r.json().get('PurchaseInvoiceIds', [])
            print(f"   ✓ {len(ids)} faktura me status 'New'")
        else:
            print(f"   ✗ {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"   ✗ {e}")
    
    # Test 5: Combine filters
    print("\n5. FILTRO: PHOENIX + 2025:")
    payload = {
        "dateFrom": date(2025, 1, 1).isoformat(),
        "dateTo": date_to.isoformat(),
        "restrictions": [
            {
                "field": "Invoice_Sender_Like",
                "values": ["PHOENIX"]
            }
        ]
    }
    
    try:
        r = s.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            ids = r.json().get('PurchaseInvoiceIds', [])
            print(f"   ✓ {len(ids)} faktura PHOENIX 2025")
        else:
            print(f"   ✗ {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"   ✗ {e}")
    
    print("\n" + "=" * 80)
    print("PËRFUNDIM: Nëse filtrat japin >50, mund të kapërcejmë limitin!")
    print("=" * 80)

if __name__ == "__main__":
    test_with_filters()
