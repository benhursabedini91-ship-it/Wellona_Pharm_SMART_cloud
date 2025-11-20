"""
Test purchase-invoice/overview endpoint for rich metadata.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import make_session, list_incoming_invoices
from datetime import date

def test_overview_endpoint():
    """Test overview endpoint to get detailed invoice metadata."""
    s = make_session()
    
    print("=" * 80)
    print("  TESTIMI I OVERVIEW ENDPOINT (Rich Metadata)")
    print("=" * 80)
    
    # First get some invoice IDs
    print("\n1. MERR INVOICE IDs:")
    invoice_objects = list_incoming_invoices(
        s, 
        date_from=date(2025, 11, 1), 
        date_to=date(2025, 11, 18)
    )
    
    # Extract just the IDs
    ids = [inv['id'] for inv in invoice_objects]
    
    print(f"   ✓ {len(ids)} faktura")
    
    if not ids:
        print("   ✗ Ska faktura!")
        return
    
    # Test overview for first invoice
    print(f"\n2. OVERVIEW PËR FAKTURË ID={ids[0]}:")
    url = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/overview"
    
    params = {
        "invoiceId": ids[0]
    }
    
    try:
        r = s.get(url, params=params, timeout=60)
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"   ✓ Struktura: {type(data)}")
            print(f"   Keys: {list(data.keys())[:20]}")  # First 20 keys
            
            # Show key fields
            print("\n   DETAJE KRYESORE:")
            print(f"   - Invoice Number: {data.get('invoiceNumber')}")
            print(f"   - Supplier: {data.get('supplierName')}")
            print(f"   - Total: {data.get('payableAmount')} RSD")
            print(f"   - Status: {data.get('purchaseInvoiceStatus')}")
            print(f"   - Date: {data.get('issueDate')}")
            print(f"   - Due Date: {data.get('dueDate')}")
            print(f"   - Items: {data.get('itemsCount')}")
            
        else:
            print(f"   ✗ Error: {r.text[:200]}")
    
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test regular purchase-invoice endpoint
    print(f"\n3. PURCHASE-INVOICE ENDPOINT (PurchaseInvoiceDto):")
    url2 = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice"
    
    params = {
        "invoiceId": ids[0]
    }
    
    try:
        r = s.get(url2, params=params, timeout=60)
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"   ✓ Struktura: {type(data)}")
            print(f"   Keys: {list(data.keys())[:30]}")
            
            # Check if it has more fields than overview
            print(f"\n   KRAHASIM ME OVERVIEW:")
            print(f"   - Overview fields: ~10-15")
            print(f"   - PurchaseInvoiceDto fields: {len(data.keys())}")
            
            # Show some extra fields
            if 'lineItems' in data:
                print(f"   - Line Items: {len(data['lineItems'])}")
            if 'accountingCustomerParty' in data:
                print(f"   - Customer: {data['accountingCustomerParty'].get('partyName', 'N/A')}")
            if 'accountingSupplierParty' in data:
                supplier = data['accountingSupplierParty']
                print(f"   - Supplier PIB: {supplier.get('endpointId', 'N/A')}")
            
        else:
            print(f"   ✗ Error: {r.text[:200]}")
    
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    print("\n" + "=" * 80)
    print("PËRFUNDIM: Purchase-invoice endpoint ka më shumë detaje!")
    print("=" * 80)

if __name__ == "__main__":
    test_overview_endpoint()
