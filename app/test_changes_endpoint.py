"""
Test purchase-invoice/changes endpoint for incremental sync.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import make_session
from datetime import date, timedelta
import time

def test_changes_endpoint():
    """Test changes endpoint to get only new/modified invoices."""
    s = make_session()
    
    url = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/changes"
    
    print("=" * 80)
    print("  TESTIMI I CHANGES ENDPOINT (Incremental Sync)")
    print("=" * 80)
    
    # Test 1: Changes from today
    print("\n1. CHANGES NGA SOT:")
    params = {
        "date": date.today().isoformat()
    }
    
    try:
        r = s.get(url, params=params, timeout=60)  # GET, not POST!
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"   Response type: {type(data)}")
            
            if isinstance(data, list):
                print(f"   ✓ {len(data)} changes")
                if data:
                    print(f"   Sample keys: {list(data[0].keys())}")
                    print(f"   First change: InvoiceId={data[0].get('invoiceId')}, Status={data[0].get('purchaseInvoiceStatus')}")
            else:
                print(f"   Keys: {list(data.keys())}")
        else:
            print(f"   ✗ Error: {r.text[:200]}")
    
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 2: Changes from yesterday
    print("\n2. CHANGES NGA DJE:")
    time.sleep(2)  # Rate limit
    params = {
        "date": (date.today() - timedelta(days=1)).isoformat()
    }
    
    try:
        r = s.post(url, json=payload, timeout=60)
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"   Response keys: {list(data.keys())}")
            print(f"   Response type: {type(data)}")
            
            # Check structure
            if isinstance(data, dict):
                for key, val in data.items():
                    if isinstance(val, list):
                        print(f"   {key}: {len(val)} items")
                    else:
                        print(f"   {key}: {val}")
            elif isinstance(data, list):
                print(f"   ✓ {len(data)} changes")
                if data:
                    print(f"   Sample: {data[0]}")
        else:
            print(f"   ✗ Error: {r.text[:200]}")
    
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 2: Changes from yesterday
    print("\n2. CHANGES NGA DJE:")
    time.sleep(2)  # Rate limit
    params = {
        "date": (date.today() - timedelta(days=1)).isoformat()
    }
    
    try:
        r = s.get(url, params=params, timeout=60)
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(f"   ✓ {len(data)} changes")
                if data:
                    # Show status distribution
                    statuses = {}
                    for item in data:
                        status = item.get('purchaseInvoiceStatus', 'Unknown')
                        statuses[status] = statuses.get(status, 0) + 1
                    print(f"   Status distribution: {statuses}")
        else:
            print(f"   ✗ Error: {r.text[:200]}")
    
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 3: Changes from 1 week ago
    print("\n3. CHANGES NGA 1 JAVË MË PARË:")
    time.sleep(2)  # Rate limit
    params = {
        "date": (date.today() - timedelta(days=7)).isoformat()
    }
    
    try:
        r = s.get(url, params=params, timeout=60)
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(f"   ✓ {len(data)} changes")
        else:
            print(f"   ✗ Error: {r.text[:200]}")
    
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    print("\n" + "=" * 80)
    print("PËRFUNDIM: Changes endpoint lejon SINKRONIZIM INCREMENTAL!")
    print("=" * 80)

if __name__ == "__main__":
    test_changes_endpoint()
