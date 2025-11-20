"""
Safe import with duplicate checking for eFaktura invoices.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime
import argparse

def check_duplicate_invoice(conn, broj_faktura, dobavljac, datum):
    """
    Check if invoice already exists in database.
    
    Args:
        conn: DB connection
        broj_faktura: Invoice number
        dobavljac: Supplier name
        datum: Invoice date
        
    Returns:
        tuple: (exists: bool, kalkid: int or None, details: str)
    """
    cursor = conn.cursor()
    
    # Try multiple schemas (FDW ebdata, public, local tables)
    schemas_to_check = ['ebdata', 'public']
    
    for schema in schemas_to_check:
        query = f"""
            SELECT kalkid, total_neto, broj_stavki, datum_unosa
            FROM {schema}.kalkopste
            WHERE broj_faktura = %s
              AND dobavljac ILIKE %s
              AND datum = %s
            ORDER BY datum_unosa DESC
            LIMIT 1
        """
        
        try:
            cursor.execute(query, (broj_faktura, f"%{dobavljac}%", datum))
            row = cursor.fetchone()
            
            if row:
                kalkid, total, stavki, datum_unosa = row
                details = f"KalkID={kalkid}, Total={total}, Stavki={stavki}, Unos={datum_unosa}, Schema={schema}"
                cursor.close()
                return (True, kalkid, details)
        except Exception:
            # Schema or table doesn't exist, try next
            continue
    
    cursor.close()
    return (False, None, "")

def import_invoices_safe(xml_dir, conn_params, force=False, dry_run=False):
    """
    Import invoices with duplicate checking.
    
    Args:
        xml_dir: Directory with XML files
        conn_params: DB connection parameters
        force: If True, import even if duplicates found
        dry_run: If True, only check without importing
    """
    print("=" * 80)
    print("  eFAKTURA IMPORT - SAFE MODE (Duplicate Check)")
    print("=" * 80)
    print(f"📂 XML Directory: {xml_dir}")
    print(f"🔒 Mode: {'DRY-RUN' if dry_run else 'LIVE IMPORT'}")
    print(f"⚠️  Force: {'YES (Import duplicates)' if force else 'NO (Skip duplicates)'}")
    print("=" * 80)
    
    # Import required modules
    try:
        from faktura_import import parse_invoice_xml, insert_kalkulacija, MP_CONFIG
    except ImportError:
        try:
            from app.faktura_import import parse_invoice_xml, insert_kalkulacija, MP_CONFIG
        except ImportError:
            print("❌ Cannot import faktura_import module!")
            return
    
    # Get XML files
    xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
    
    if not xml_files:
        print("⚠️  Nuk u gjetën XML files!")
        return
    
    print(f"\n📋 {len(xml_files)} XML files gjetur\n")
    
    # Connect to DB
    try:
        conn = psycopg2.connect(**conn_params)
        print(f"✓ Connected to DB: {conn_params['dbname']} @ {conn_params['host']}\n")
    except Exception as e:
        print(f"❌ DB Connection failed: {e}")
        return
    
    stats = {
        'total': len(xml_files),
        'imported': 0,
        'skipped_duplicate': 0,
        'failed': 0,
        'errors': []
    }
    
    # Process each XML
    for idx, xml_file in enumerate(xml_files, 1):
        xml_path = os.path.join(xml_dir, xml_file)
        print(f"[{idx}/{len(xml_files)}] {xml_file}")
        
        try:
            # Parse XML
            header, items = parse_invoice_xml(xml_path)
            
            broj = header.get('broj_faktura', 'N/A')
            dobavljac = header.get('dobavljac', 'N/A')
            datum = header.get('datum', 'N/A')
            total = header.get('total_neto', 0)
            
            print(f"  📄 {broj} | {dobavljac} | {datum} | {total:.2f} RSD")
            print(f"  📦 {len(items)} artikuj")
            
            # Check for duplicate
            exists, kalkid, details = check_duplicate_invoice(conn, broj, dobavljac, datum)
            
            if exists:
                print(f"  ⚠️  DUPLIKAT! {details}")
                
                if not force:
                    stats['skipped_duplicate'] += 1
                    print(f"  ⊙ Anashkaluar (use --force për të importuar)")
                    continue
                else:
                    print(f"  ⚡ FORCE MODE - do të importoj përsëri!")
            
            # Import
            if dry_run:
                print(f"  🔍 DRY-RUN: Do të importohej")
                stats['imported'] += 1
            else:
                kalk_id = insert_kalkulacija(
                    conn,
                    header,
                    items,
                    MP_CONFIG,
                    dokvrsta='20',
                    magacin='101',
                    periodid=4,
                    userid=14,
                    dry_run=False,
                    allow_remote_write=True
                )
                
                if kalk_id:
                    stats['imported'] += 1
                    print(f"  ✓ IMPORTUAR (KalkID={kalk_id})")
                else:
                    stats['skipped_duplicate'] += 1
                    print(f"  ⊙ Anashkaluar (insert_kalkulacija returned None)")
        
        except Exception as e:
            stats['failed'] += 1
            error_msg = f"{xml_file}: {str(e)}"
            stats['errors'].append(error_msg)
            print(f"  ❌ ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("  PËRFUNDIM")
    print("=" * 80)
    print(f"📋 Total XML: {stats['total']}")
    print(f"✓ Importuar: {stats['imported']}")
    print(f"⊙ Duplikate (anashkaluar): {stats['skipped_duplicate']}")
    print(f"❌ Dështuan: {stats['failed']}")
    
    if stats['errors']:
        print(f"\n⚠️  Gabime ({len(stats['errors'])}):")
        for err in stats['errors'][:5]:
            print(f"  - {err}")
    
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import eFaktura XMLs safely (duplicate check)')
    parser.add_argument('--xml-dir', default='../staging/faktura_uploads', help='XML directory')
    parser.add_argument('--force', action='store_true', help='Import even if duplicates exist')
    parser.add_argument('--dry-run', action='store_true', help='Check only, do not import')
    parser.add_argument('--host', default='localhost', help='DB host')
    parser.add_argument('--port', default='5432', help='DB port')
    parser.add_argument('--dbname', default='wph_ai', help='DB name')
    parser.add_argument('--user', default='postgres', help='DB user')
    
    args = parser.parse_args()
    
    # Get password from env or prompt
    password = os.getenv('WPH_DB_PASS')
    if not password:
        from getpass import getpass
        password = getpass("DB Password: ")
    
    conn_params = {
        'host': args.host,
        'port': int(args.port),
        'dbname': args.dbname,
        'user': args.user,
        'password': password,
        'application_name': 'eFaktura_SafeImport'
    }
    
    import_invoices_safe(args.xml_dir, conn_params, args.force, args.dry_run)
