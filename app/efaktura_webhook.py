"""
eFaktura Webhook Management - Subscribe for automatic invoice notifications.

IMPORTANT: Subscription is for NEXT DAY ONLY (expires after 24h).
You need to re-subscribe daily or set up a cron job.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import make_session
from datetime import datetime

def subscribe_for_notifications():
    """
    Subscribe to receive invoice status change notifications.
    
    Returns subscription ID (GUID) if successful.
    NOTE: Subscription is valid for NEXT DAY only!
    """
    s = make_session()
    url = "https://efaktura.mfin.gov.rs/api/publicApi/subscribe"
    
    print("=" * 80)
    print("  SUBSCRIBE FOR INVOICE NOTIFICATIONS")
    print("=" * 80)
    
    try:
        # POST with empty body
        r = s.post(url, data='', timeout=60)
        
        print(f"\n📡 Request: POST {url}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Status: {r.status_code}")
        
        if r.status_code == 200:
            subscription_id = r.text.strip()
            print(f"\n✅ SUBSCRIPTION SUCCESSFUL!")
            print(f"🆔 Subscription ID: {subscription_id}")
            print(f"\n⚠️  IMPORTANT:")
            print(f"   - Subscription is valid for NEXT DAY only (expires in 24h)")
            print(f"   - You will receive notifications for invoice status changes")
            print(f"   - Notifications will be sent to your registered endpoint")
            print(f"   - Re-subscribe daily to maintain continuous monitoring")
            
            # Save to file for future reference
            with open("efaktura_subscription_id.txt", "w", encoding="utf-8") as f:
                f.write(f"Subscription ID: {subscription_id}\n")
                f.write(f"Subscribed at: {datetime.now().isoformat()}\n")
                f.write(f"Valid until: {datetime.now().date()} + 1 day\n")
            
            print(f"\n💾 Subscription ID saved to: efaktura_subscription_id.txt")
            
            return subscription_id
        
        else:
            print(f"\n❌ SUBSCRIPTION FAILED")
            print(f"Response: {r.text[:500]}")
            return None
    
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        return None
    
    finally:
        print("\n" + "=" * 80)


def check_subscription_status(subscription_id=None):
    """
    Check if subscription is still active.
    
    NOTE: There might not be a GET endpoint to check status.
    This will try common patterns.
    """
    s = make_session()
    
    if subscription_id is None:
        # Try to read from file
        try:
            with open("efaktura_subscription_id.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("Subscription ID:"):
                        subscription_id = line.split(":")[1].strip()
                        break
        except:
            print("❌ No subscription ID found. Run subscribe_for_notifications() first.")
            return
    
    print(f"\n🔍 Checking subscription: {subscription_id}")
    
    # Try GET
    url = f"https://efaktura.mfin.gov.rs/api/publicApi/subscribe/{subscription_id}"
    
    try:
        r = s.get(url, timeout=60)
        print(f"GET Status: {r.status_code}")
        
        if r.status_code == 200:
            print(f"✅ Subscription active: {r.text}")
        elif r.status_code == 404:
            print(f"❌ Subscription not found or expired")
        else:
            print(f"Response: {r.text[:200]}")
    
    except Exception as e:
        print(f"Exception: {e}")


def unsubscribe(subscription_id=None):
    """
    Unsubscribe from notifications.
    
    NOTE: There might not be an unsubscribe endpoint.
    Subscriptions expire automatically after 24h.
    """
    s = make_session()
    
    if subscription_id is None:
        try:
            with open("efaktura_subscription_id.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("Subscription ID:"):
                        subscription_id = line.split(":")[1].strip()
                        break
        except:
            print("❌ No subscription ID found.")
            return
    
    print(f"\n🛑 Attempting to unsubscribe: {subscription_id}")
    
    # Try DELETE
    url = f"https://efaktura.mfin.gov.rs/api/publicApi/subscribe/{subscription_id}"
    
    try:
        r = s.delete(url, timeout=60)
        print(f"DELETE Status: {r.status_code}")
        
        if r.status_code in [200, 204]:
            print(f"✅ Unsubscribed successfully")
        elif r.status_code == 404:
            print(f"⚠️  Subscription not found (maybe already expired)")
        else:
            print(f"Response: {r.text[:200]}")
    
    except Exception as e:
        print(f"Exception: {e}")


def setup_daily_subscription_cron():
    """
    Generate a PowerShell script for daily subscription renewal.
    """
    script_content = """# eFaktura Daily Subscription Renewal
# Run this script daily via Task Scheduler

$ErrorActionPreference = "Stop"

# Set API key
$env:WPH_EFAKT_API_KEY = "f7b40af0-9689-4872-8d59-4779f7961175"

# Change to script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Run subscription
Write-Host "=== eFaktura Daily Subscription ===" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

python -c "from efaktura_webhook import subscribe_for_notifications; subscribe_for_notifications()"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Subscription renewed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Subscription failed" -ForegroundColor Red
    exit 1
}
"""
    
    with open("efaktura_daily_subscribe.ps1", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print("\n📝 Created: efaktura_daily_subscribe.ps1")
    print("\n📅 To schedule daily renewal:")
    print("   1. Open Task Scheduler")
    print("   2. Create new task:")
    print("      - Trigger: Daily at 6:00 AM")
    print("      - Action: powershell.exe -File efaktura_daily_subscribe.ps1")
    print("      - Start in: C:\\Wellona\\Wellona_Pharm_SMART\\app")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "subscribe":
            subscribe_for_notifications()
        
        elif cmd == "check":
            check_subscription_status()
        
        elif cmd == "unsubscribe":
            unsubscribe()
        
        elif cmd == "setup-cron":
            setup_daily_subscription_cron()
        
        else:
            print(f"Unknown command: {cmd}")
            print("Usage:")
            print("  python efaktura_webhook.py subscribe")
            print("  python efaktura_webhook.py check")
            print("  python efaktura_webhook.py unsubscribe")
            print("  python efaktura_webhook.py setup-cron")
    
    else:
        # Default: subscribe
        subscribe_for_notifications()
