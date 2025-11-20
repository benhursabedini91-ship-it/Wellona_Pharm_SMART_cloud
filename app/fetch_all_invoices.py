# file: app/fetch_all_invoices.py
"""
Script për të shkarkuar të gjitha fakturat XML nga eFaktura dhe (opsionalisht) për t'i importuar në ERP.

PËRDORIMI:
  1. Vendos variablat e mjedisit:
     $env:WPH_EFAKT_API_KEY = "your-api-key-here"
     $env:WPH_EFAKT_LIST_URL = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/ids?dateFrom={fromDate}&dateTo={toDate}"
     $env:WPH_EFAKT_GET_XML_URL = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/xml/{invoiceId}"
     
  2. Ekzekuto:
     python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18
     
  3. Për import automatik në ERP:
     python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18 --auto-import
     
  4. Për dry-run (shikon çfarë do bëjë pa shkruar në DB):
     python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18 --auto-import --dry-run
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import time

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.efaktura_client import (
    make_session, 
    list_incoming_invoices, 
    download_invoice_xml,
    save_xml_to_staging,
    EFakturaError
)

def ensure_utf8():
    """Ensure UTF-8 encoding for console output."""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def fetch_all_invoices(date_from, date_to, output_dir=None, delay_between_downloads=0.5):
    """
    Fetch të gjitha fakturat nga eFaktura për periudhën e specifikuar.
    
    Args:
        date_from: Data fillestare (datetime.date ose string YYYY-MM-DD)
        date_to: Data përfundimtare (datetime.date ose string YYYY-MM-DD)
        output_dir: Direktoria ku ruhen XML-të (default: staging/faktura_uploads)
        delay_between_downloads: Delay në sekonda midis shkarkimeve (për të shmangur rate limits)
    
    Returns:
        dict: {
            'total': numri total i fakturave,
            'downloaded': numri i shkarkuara me sukses,
            'failed': numri i dështuara,
            'paths': lista e path-eve të shkarkuara,
            'errors': lista e gabimeve
        }
    """
    ensure_utf8()
    
    # Parse dates if strings
    if isinstance(date_from, str):
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    if isinstance(date_to, str):
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Default output directory
    if not output_dir:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'staging', 
            'faktura_uploads'
        )
    
    print(f"🔍 Duke kërkuar faktura nga {date_from} deri në {date_to}...")
    print(f"📂 Direktoria e output: {output_dir}")
    print("=" * 80)
    
    results = {
        'total': 0,
        'downloaded': 0,
        'failed': 0,
        'paths': [],
        'errors': []
    }
    
    try:
        # Create session
        session = make_session()
        print("✓ Sesioni me eFaktura API u krijua")
        
        # Get list of invoices
        print(f"\n📋 Duke marrë listën e fakturave...")
        invoices = list_incoming_invoices(session, date_from, date_to)
        results['total'] = len(invoices)
        
        if not invoices:
            print("⚠️  Nuk u gjetën faktura për këtë periudhë")
            return results
        
        print(f"✓ U gjetën {len(invoices)} faktura")
        print("=" * 80)
        
        # Download each invoice
        for idx, inv in enumerate(invoices, 1):
            invoice_id = inv.get('id')
            supplier = inv.get('supplier', 'UNKNOWN')
            invoice_no = inv.get('invoice_no', 'NO_NUM')
            issue_date = inv.get('issue_date', '')
            
            print(f"\n[{idx}/{len(invoices)}] Faktura: {invoice_no}")
            print(f"  Furnitori: {supplier}")
            print(f"  Data: {issue_date}")
            print(f"  ID: {invoice_id}")
            
            try:
                # Download XML
                xml_content = download_invoice_xml(session, invoice_id)
                
                # Save to file (pass invoice_id for unique filename)
                file_path = save_xml_to_staging(
                    xml_content, 
                    output_dir, 
                    supplier, 
                    invoice_no, 
                    issue_date,
                    invoice_id
                )
                
                results['downloaded'] += 1
                results['paths'].append(file_path)
                
                print(f"  ✓ Shkarkuar: {os.path.basename(file_path)}")
                
                # Delay to avoid rate limiting
                if delay_between_downloads > 0 and idx < len(invoices):
                    time.sleep(delay_between_downloads)
                    
            except Exception as e:
                results['failed'] += 1
                error_msg = f"Invoice {invoice_no} (ID: {invoice_id}): {str(e)}"
                results['errors'].append(error_msg)
                print(f"  ❌ Gabim: {str(e)}")
        
        print("\n" + "=" * 80)
        print("📊 PËRMBLEDHJE:")
        print(f"  Total faktura: {results['total']}")
        print(f"  ✓ Shkarkuar me sukses: {results['downloaded']}")
        print(f"  ❌ Dështuan: {results['failed']}")
        
        if results['errors']:
            print("\n⚠️  GABIME:")
            for error in results['errors']:
                print(f"  - {error}")
        
        return results
        
    except EFakturaError as e:
        print(f"\n❌ Gabim në eFaktura API: {e}")
        results['errors'].append(str(e))
        return results
    except Exception as e:
        print(f"\n❌ Gabim i papritur: {e}")
        import traceback
        traceback.print_exc()
        results['errors'].append(str(e))
        return results

def auto_import_invoices(xml_paths, dry_run=False):
    """
    Import automatik i fakturave XML në ERP.
    
    Args:
        xml_paths: Lista e path-eve të XML-ve
        dry_run: Nëse True, bën vetëm validim pa shkruar në DB
    
    Returns:
        dict: Statistika e importit
    """
    ensure_utf8()
    
    print("\n" + "=" * 80)
    print("🔄 FILLIM I IMPORTIT AUTOMATIK NË ERP")
    print("=" * 80)
    
    if dry_run:
        print("⚠️  DRY-RUN MODE: Nuk do të shkruhet në bazë")
    
    stats = {
        'total': len(xml_paths),
        'imported': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    # Import faktura_import functions
    try:
        from app.faktura_import import (
            parse_invoice_xml,
            insert_kalkulacija,
            MP_CONFIG,
            DB_DEFAULTS
        )
        import psycopg2
    except ImportError as e:
        print(f"❌ Nuk mund të importoj modület e nevojshëm: {e}")
        stats['errors'].append(str(e))
        return stats
    
    # Setup DB connection
    try:
        db_cfg = {
            'dbname': os.getenv('WPH_DB_NAME', DB_DEFAULTS['dbname']),
            'user': os.getenv('WPH_DB_USER', DB_DEFAULTS['user']),
            'password': os.getenv('WPH_DB_PASS', DB_DEFAULTS['password']),
            'host': os.getenv('WPH_DB_HOST', DB_DEFAULTS['host']),
            'port': int(os.getenv('WPH_DB_PORT', str(DB_DEFAULTS['port']))),
            'application_name': 'wphAI_auto_import'
        }
        
        if not db_cfg['password']:
            from getpass import getpass
            db_cfg['password'] = getpass("DB password: ")
        
        conn = psycopg2.connect(**db_cfg)
        print(f"✓ Lidhur me DB: {db_cfg['dbname']} @ {db_cfg['host']}")
        
    except Exception as e:
        print(f"❌ Gabim në lidhjen me DB: {e}")
        stats['errors'].append(str(e))
        return stats
    
    # Process each XML
    for idx, xml_path in enumerate(xml_paths, 1):
        print(f"\n[{idx}/{len(xml_paths)}] Importimi i: {os.path.basename(xml_path)}")
        
        try:
            # Parse XML
            header, items = parse_invoice_xml(xml_path)
            
            print(f"  Faktura: {header['broj_faktura']}")
            print(f"  Furnitori: {header['dobavljac']}")
            print(f"  Data: {header['datum']}")
            print(f"  Artikuj: {len(items)}")
            print(f"  Total neto: {header['total_neto']}")
            
            # Get remote write permission from env
            allow_remote = os.getenv('WPH_WRITE_REMOTE', '0') == '1'
            
            # Insert kalkulacija
            kalk_id = insert_kalkulacija(
                conn, 
                header, 
                items, 
                MP_CONFIG,
                dokvrsta='20',
                magacin='101',
                komintent='1',  # Will be auto-resolved from dobavljac
                periodid=4,
                userid=14,
                dry_run=dry_run,
                allow_remote_write=allow_remote
            )
            
            if kalk_id:
                stats['imported'] += 1
                print(f"  ✓ Importuar me sukses (kalkid={kalk_id})")
            else:
                stats['skipped'] += 1
                print(f"  ⚠️  Kalkulacija nuk u krijua (ndoshta ekziston)")
                
        except Exception as e:
            stats['failed'] += 1
            error_msg = f"{os.path.basename(xml_path)}: {str(e)}"
            stats['errors'].append(error_msg)
            print(f"  ❌ Gabim: {e}")
            import traceback
            traceback.print_exc()
    
    # Close connection
    conn.close()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 PËRMBLEDHJE E IMPORTIT:")
    print(f"  Total XML: {stats['total']}")
    print(f"  ✓ Importuar: {stats['imported']}")
    print(f"  ⚠️  Kaluar (skip): {stats['skipped']}")
    print(f"  ❌ Dështuan: {stats['failed']}")
    
    if stats['errors']:
        print("\n⚠️  GABIME:")
        for error in stats['errors']:
            print(f"  - {error}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(
        description='Shkarkimi i të gjitha fakturave XML nga eFaktura',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SHEMBUJ:
  # Shkarko fakturat e muajit të kaluar
  python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31
  
  # Shkarko dhe importo automatikisht
  python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --auto-import
  
  # Dry-run për të parë çfarë do të bëjë
  python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --auto-import --dry-run
  
  # Shkarko fakturat e vitit 2025
  python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-12-31 --output ./fakturat_2025

VARIABLAT E MJEDISIT:
  WPH_EFAKT_API_KEY        - API key për eFaktura (e detyrueshme)
  WPH_EFAKT_LIST_URL       - URL për listën e fakturave
  WPH_EFAKT_GET_XML_URL    - URL për shkarkimin e XML
  WPH_DB_NAME              - Emri i bazës së të dhënave (default: wph_ai)
  WPH_DB_USER              - Përdoruesi i DB (default: postgres)
  WPH_DB_PASS              - Fjalëkalimi i DB
  WPH_DB_HOST              - Host i DB (default: 127.0.0.1)
  WPH_DB_PORT              - Port i DB (default: 5432)
  WPH_WRITE_REMOTE         - Lejo shkrim në DB remote (0=jo, 1=po)
  WPH_ALLOW_AUTO_CREATE    - Lejo krijim automatik të artikujve (0=jo, 1=po)
        """
    )
    
    parser.add_argument(
        '--from', 
        dest='date_from',
        required=True,
        help='Data fillestare (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--to',
        dest='date_to', 
        required=True,
        help='Data përfundimtare (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--output',
        dest='output_dir',
        help='Direktoria ku ruhen XML-të (default: staging/faktura_uploads)'
    )
    
    parser.add_argument(
        '--auto-import',
        action='store_true',
        help='Importo automatikisht fakturat në ERP pas shkarkimit'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry-run mode: shikon çfarë do bëjë pa shkruar në DB'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay në sekonda midis shkarkimeve (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    # Validate API key
    api_key = os.getenv('WPH_EFAKT_API_KEY')
    if not api_key:
        print("❌ GABIM: WPH_EFAKT_API_KEY nuk është vendosur!")
        print("\nVendose API key:")
        print('  $env:WPH_EFAKT_API_KEY = "your-api-key-here"')
        sys.exit(1)
    
    # Validate URLs
    list_url = os.getenv('WPH_EFAKT_LIST_URL')
    get_url = os.getenv('WPH_EFAKT_GET_XML_URL')
    
    if not list_url or not get_url:
        print("⚠️  URL-të e eFaktura nuk janë vendosur. Duke përdorur default...")
        print("\nPër të vendosur manualisht:")
        print('  $env:WPH_EFAKT_LIST_URL = "https://efaktura.../api/.../invoices?from={fromDate}&to={toDate}"')
        print('  $env:WPH_EFAKT_GET_XML_URL = "https://efaktura.../api/.../invoices/{invoiceId}/xml"')
    
    ensure_utf8()
    
    # Banner
    print("=" * 80)
    print("  eFAKTURA XML DOWNLOADER & AUTO-IMPORTER")
    print("  Wellona Pharm AI System")
    print("=" * 80)
    print(f"Periudha: {args.date_from} deri {args.date_to}")
    if args.auto_import:
        print("Mode: Shkarkim + Import automatik")
        if args.dry_run:
            print("⚠️  DRY-RUN: Nuk do të shkruhet në bazë")
    else:
        print("Mode: Vetëm shkarkim")
    print("=" * 80)
    
    # Fetch invoices
    results = fetch_all_invoices(
        args.date_from,
        args.date_to,
        args.output_dir,
        args.delay
    )
    
    # Auto-import if requested
    if args.auto_import and results['downloaded'] > 0:
        import_stats = auto_import_invoices(results['paths'], args.dry_run)
        
        # Combined summary
        print("\n" + "=" * 80)
        print("🎯 PËRMBLEDHJE FINALE:")
        print("=" * 80)
        print(f"📥 SHKARKIME:")
        print(f"   Total: {results['total']}")
        print(f"   ✓ Sukses: {results['downloaded']}")
        print(f"   ❌ Dështuan: {results['failed']}")
        print(f"\n💾 IMPORT:")
        print(f"   Total: {import_stats['total']}")
        print(f"   ✓ Importuar: {import_stats['imported']}")
        print(f"   ⚠️  Skip: {import_stats['skipped']}")
        print(f"   ❌ Dështuan: {import_stats['failed']}")
        print("=" * 80)
    
    # Exit code
    if results['failed'] > 0 or (args.auto_import and import_stats.get('failed', 0) > 0):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()
