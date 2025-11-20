# Quick test për eFaktura API
import os
import sys
from datetime import datetime, timedelta

# Set your API key here for testing
os.environ['WPH_EFAKT_API_KEY'] = 'f7b40af0-9689-4872-8d59-4779f7961175'
os.environ['WPH_EFAKT_API_BASE'] = 'https://efaktura.mfin.gov.rs'
# Correct endpoints based on Swagger documentation
os.environ['WPH_EFAKT_LIST_URL'] = 'https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/ids'
os.environ['WPH_EFAKT_GET_XML_URL'] = 'https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/xml'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.efaktura_client import make_session, list_incoming_invoices, download_invoice_xml

print("=" * 80)
print("TEST - eFaktura API (Serbia)")
print("=" * 80)

# Test 1: Create session
print("\n1. Duke krijuar session...")
try:
    session = make_session()
    print(f"   ✓ Session OK")
    print(f"   Headers: {dict(session.headers)}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: List invoices (last 7 days)
print("\n2. Duke listuar faktura (3 muajt e fundit)...")
date_to = datetime.now().date()
date_from = date_to - timedelta(days=90)  # Try 3 months
print(f"   Periudha: {date_from} deri {date_to}")

try:
    invoices = list_incoming_invoices(session, date_from, date_to)
    print(f"   ✓ U gjetën {len(invoices)} faktura")
    
    if invoices:
        print("\n   Shembuj:")
        for inv in invoices[:3]:
            print(f"     • ID: {inv['id']}")
            print(f"       Supplier: {inv.get('supplier', 'N/A')}")
            print(f"       Number: {inv.get('invoice_no', 'N/A')}")
            print(f"       Date: {inv.get('issue_date', 'N/A')}")
            print()
        
        # Test 3: Download XML for first invoice
        if invoices:
            print("\n3. Duke shkarkuar XML për faturën e parë...")
            first_id = invoices[0]['id']
            print(f"   Invoice ID: {first_id}")
            
            try:
                xml_content = download_invoice_xml(session, first_id)
                print(f"   ✓ XML shkarkuar: {len(xml_content)} bytes")
                print(f"   Fillimi: {xml_content[:200]}")
            except Exception as e:
                print(f"   ✗ Error: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("\n   ⚠️  Nuk ka faktura për këtë periudhë. Provo një periudhë më të gjatë:")
        print(f"   date_from = {(datetime.now() - timedelta(days=30)).date()}")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ Test i plotë!")
print("=" * 80)
