"""
Test webhook subscription endpoint for real-time notifications.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import make_session

def test_webhook_subscription():
    """Test webhook subscription for automatic invoice notifications."""
    s = make_session()
    
    url = "https://efaktura.mfin.gov.rs/api/publicApi/subscribe"
    
    print("=" * 80)
    print("  TESTIMI I WEBHOOK SUBSCRIPTION")
    print("=" * 80)
    
    # Test 1: Check current subscription status
    print("\n1. CHECK CURRENT SUBSCRIPTION:")
    try:
        # Try GET first to see current status
        r = s.get(url, timeout=60)
        print(f"   GET Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print(f"   ✓ Current subscription: {data}")
        else:
            print(f"   Response: {r.text[:300]}")
    
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 2: Try to subscribe with a test URL
    print("\n2. SUBSCRIBE ME TEST URL:")
    print("   ⚠️  KY ËSHTË TEST - mos e ekzekuto nëse nuk ke webhook server!")
    print("   (Komento këtë pjesë nëse don me ekzekutu)")
    
    # UNCOMMENT TO TEST:
    # payload = {
    #     "url": "https://webhook.site/unique-test-url",  # Test webhook catcher
    #     "events": ["InvoiceReceived", "InvoiceStatusChanged"]
    # }
    # 
    # try:
    #     r = s.post(url, json=payload, timeout=60)
    #     print(f"   POST Status: {r.status_code}")
    #     
    #     if r.status_code == 200:
    #         print(f"   ✓ Subscription successful!")
    #         data = r.json()
    #         print(f"   Response: {data}")
    #     else:
    #         print(f"   ✗ Error: {r.text[:300]}")
    # 
    # except Exception as e:
    #     print(f"   ✗ Exception: {e}")
    
    print("   [SKIPPED - Uncomment në kod për test]")
    
    # Test 3: Check Swagger schema
    print("\n3. SWAGGER SCHEMA:")
    print("   Expected request body:")
    print("   {")
    print('     "url": "string",')
    print('     "events": ["string"]')
    print("   }")
    print("")
    print("   Possible events:")
    print("   - InvoiceReceived")
    print("   - InvoiceStatusChanged")
    print("   - InvoiceApproved")
    print("   - InvoiceRejected")
    print("   (Check Swagger për listë të plotë)")
    
    print("\n" + "=" * 80)
    print("PËRFUNDIM: Webhook subscription është endpoint më i rëndësishëm!")
    print("Rekomandim: Krijo webhook server dhe regjistrohu për notifications.")
    print("=" * 80)

if __name__ == "__main__":
    test_webhook_subscription()
