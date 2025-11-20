"""
Fetch ALL invoices by breaking down into daily requests.
Bypasses the 50-invoice API limit.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import make_session, list_incoming_invoices, download_invoice_xml, save_xml_to_staging
from datetime import date, timedelta
import time
import argparse

def fetch_all_by_day(date_from, date_to, output_dir=None, delay=0.3):
    """
    Fetch invoices day-by-day to bypass 50-invoice limit.
    
    Args:
        date_from: Start date
        date_to: End date
        output_dir: Output directory for XML files
        delay: Delay between requests (seconds)
    
    Returns:
        dict with results
    """
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)
    if isinstance(date_to, str):
        date_to = date.fromisoformat(date_to)
    
    if not output_dir:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'staging', 
            'faktura_uploads'
        )
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("  eFAKTURA DOWNLOADER - DAY BY DAY MODE")
    print("  (Bypass 50-invoice API limit)")
    print("=" * 80)
    print(f"📅 Periudha: {date_from} deri {date_to}")
    print(f"📂 Output: {output_dir}")
    print("=" * 80)
    
    session = make_session()
    
    results = {
        'total_invoices': 0,
        'downloaded': 0,
        'failed': 0,
        'skipped_existing': 0,
        'days_processed': 0,
        'errors': []
    }
    
    all_invoice_ids = set()  # Track unique IDs
    current_date = date_from
    
    while current_date <= date_to:
        results['days_processed'] += 1
        
        print(f"\n📆 {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A')})")
        
        try:
            # Get invoices for this day
            invoices = list_incoming_invoices(session, current_date, current_date)
            
            if not invoices:
                print(f"   ø Nuk ka faktura")
            else:
                print(f"   ✓ {len(invoices)} faktura gjetur")
                
                # Download each invoice
                for inv in invoices:
                    invoice_id = inv.get('id')
                    
                    # Skip if already downloaded
                    if invoice_id in all_invoice_ids:
                        results['skipped_existing'] += 1
                        continue
                    
                    all_invoice_ids.add(invoice_id)
                    results['total_invoices'] += 1
                    
                    supplier = inv.get('supplier', '')
                    invoice_no = inv.get('invoice_no', '')
                    issue_date = inv.get('issue_date', '')
                    
                    # Check if file already exists
                    filename = f"INV_{invoice_id}.xml"
                    filepath = os.path.join(output_dir, filename)
                    
                    if os.path.exists(filepath):
                        print(f"     ⊙ {filename} (ekziston)")
                        results['skipped_existing'] += 1
                        continue
                    
                    try:
                        # Download
                        xml_content = download_invoice_xml(session, invoice_id)
                        
                        # Save
                        saved_path = save_xml_to_staging(
                            xml_content,
                            output_dir,
                            supplier,
                            invoice_no,
                            issue_date,
                            invoice_id
                        )
                        
                        results['downloaded'] += 1
                        print(f"     ✓ {filename}")
                        
                        # Small delay
                        time.sleep(delay)
                        
                    except Exception as e:
                        results['failed'] += 1
                        error_msg = f"ID {invoice_id}: {str(e)}"
                        results['errors'].append(error_msg)
                        print(f"     ✗ {filename} - {e}")
            
            # Delay between days (respect rate limit: max 3 req/sec)
            time.sleep(max(delay, 0.4))
            
        except Exception as e:
            print(f"   ✗ Gabim: {e}")
            results['errors'].append(f"Date {current_date}: {str(e)}")
        
        # Next day
        current_date += timedelta(days=1)
    
    # Summary
    print("\n" + "=" * 80)
    print("  PËRFUNDIM")
    print("=" * 80)
    print(f"📆 Ditë të kontrolluara: {results['days_processed']}")
    print(f"📋 Faktura të gjetura: {results['total_invoices']}")
    print(f"✓ Të shkarkuara: {results['downloaded']}")
    print(f"⊙ Ekzistonin më parë: {results['skipped_existing']}")
    print(f"✗ Dështuan: {results['failed']}")
    
    if results['errors']:
        print(f"\n⚠️  Gabime ({len(results['errors'])}):")
        for err in results['errors'][:10]:  # Show first 10
            print(f"  - {err}")
    
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch ALL invoices day-by-day from eFaktura')
    parser.add_argument('--from', dest='date_from', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to', dest='date_to', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', dest='output_dir', help='Output directory')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    
    args = parser.parse_args()
    
    fetch_all_by_day(
        args.date_from,
        args.date_to,
        args.output_dir,
        args.delay
    )
