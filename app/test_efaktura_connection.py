# test_efaktura_connection.py
"""
Test script për të verifikuar që eFaktura integration është konfiguruar saktë.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_env_vars():
    """Test nëse variablat e mjedisit janë vendosur."""
    print("=" * 80)
    print("TEST 1: Variablat e mjedisit")
    print("=" * 80)
    
    required = {
        'WPH_EFAKT_API_KEY': 'API Key',
    }
    
    optional = {
        'WPH_EFAKT_API_BASE': 'API Base URL',
        'WPH_EFAKT_LIST_URL': 'LIST endpoint URL',
        'WPH_EFAKT_GET_XML_URL': 'GET XML endpoint URL',
        'WPH_DB_NAME': 'Database name',
        'WPH_DB_USER': 'Database user',
        'WPH_DB_HOST': 'Database host',
        'WPH_DB_PORT': 'Database port',
    }
    
    all_ok = True
    
    print("\n📋 Të detyrueshme:")
    for var, desc in required.items():
        val = os.getenv(var)
        if val:
            # Mask sensitive data
            if 'KEY' in var or 'PASS' in var:
                display = val[:10] + '...' if len(val) > 10 else '***'
            else:
                display = val[:50] + '...' if len(val) > 50 else val
            print(f"  ✓ {desc:30} {display}")
        else:
            print(f"  ✗ {desc:30} MUNGON")
            all_ok = False
    
    print("\n📋 Opsionale:")
    for var, desc in optional.items():
        val = os.getenv(var)
        if val:
            display = val[:50] + '...' if len(val) > 50 else val
            print(f"  ✓ {desc:30} {display}")
        else:
            print(f"  ⚠ {desc:30} (do të përdoret default)")
    
    print()
    return all_ok

def test_api_connection():
    """Test lidhjen me eFaktura API."""
    print("=" * 80)
    print("TEST 2: Lidhja me eFaktura API")
    print("=" * 80)
    print()
    
    try:
        from app.efaktura_client import make_session
        
        print("📡 Duke krijuar session...")
        session = make_session()
        print("  ✓ Session u krijua me sukses")
        
        # Test headers
        print("\n📋 Headers:")
        for key, val in session.headers.items():
            if 'key' in key.lower() or 'auth' in key.lower():
                display = val[:10] + '...' if len(val) > 10 else '***'
            else:
                display = val
            print(f"  {key}: {display}")
        
        print("\n✓ API connection OK")
        return True
        
    except Exception as e:
        print(f"\n✗ API connection dështoi: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_list():
    """Test listimin e fakturave (shembull i vogël)."""
    print("\n" + "=" * 80)
    print("TEST 3: Listimi i fakturave (test i vogël)")
    print("=" * 80)
    print()
    
    try:
        from app.efaktura_client import make_session, list_incoming_invoices
        
        # Test me javën e kaluar
        date_to = datetime.now().date()
        date_from = date_to - timedelta(days=7)
        
        print(f"📅 Periudha: {date_from} deri {date_to}")
        
        session = make_session()
        print("📡 Duke kërkuar faktura...")
        
        invoices = list_incoming_invoices(session, date_from, date_to)
        
        print(f"\n✓ U gjetën {len(invoices)} faktura")
        
        if invoices:
            print("\n📋 Shembuj (5 të parat):")
            for inv in invoices[:5]:
                print(f"  • {inv.get('invoice_no', 'N/A'):20} {inv.get('supplier', 'N/A'):30} {inv.get('issue_date', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Listimi dështoi: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_db_connection():
    """Test lidhjen me bazën e të dhënave."""
    print("\n" + "=" * 80)
    print("TEST 4: Lidhja me Database")
    print("=" * 80)
    print()
    
    try:
        import psycopg2
        
        db_cfg = {
            'dbname': os.getenv('WPH_DB_NAME', 'wph_ai'),
            'user': os.getenv('WPH_DB_USER', 'postgres'),
            'password': os.getenv('WPH_DB_PASS', ''),
            'host': os.getenv('WPH_DB_HOST', '127.0.0.1'),
            'port': int(os.getenv('WPH_DB_PORT', '5432')),
        }
        
        print(f"📡 Duke u lidhur me {db_cfg['dbname']} @ {db_cfg['host']}:{db_cfg['port']}...")
        
        if not db_cfg['password']:
            print("  ⚠ Password nuk është vendosur (OK për test, por duhet për import)")
            return None
        
        conn = psycopg2.connect(**db_cfg)
        
        # Test query
        cur = conn.cursor()
        cur.execute("SELECT current_database(), current_user, version()")
        row = cur.fetchone()
        
        print(f"  ✓ Lidhur me sukses")
        print(f"\n📋 Info:")
        print(f"  Database: {row[0]}")
        print(f"  User: {row[1]}")
        print(f"  Version: {row[2][:50]}...")
        
        # Check schemas
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('public', 'eb_fdw', 'wph_core', 'ref') ORDER BY schema_name")
        schemas = [r[0] for r in cur.fetchall()]
        print(f"\n📋 Schemas: {', '.join(schemas)}")
        
        cur.close()
        conn.close()
        
        print("\n✓ Database connection OK")
        return True
        
    except Exception as e:
        print(f"\n✗ Database connection dështoi: {e}")
        if 'password' in str(e).lower():
            print("\n💡 Tip: Vendos DB password:")
            print("  $env:WPH_DB_PASS = 'your-password'")
        return False

def main():
    print("\n")
    print("█" * 80)
    print("  eFAKTURA INTEGRATION - TEST SUITE")
    print("  Wellona Pharm SMART System")
    print("█" * 80)
    print()
    
    results = {}
    
    # Run tests
    results['env'] = test_env_vars()
    
    if results['env']:
        results['api_conn'] = test_api_connection()
        
        if results['api_conn']:
            results['api_list'] = test_api_list()
        else:
            results['api_list'] = False
            print("\n⚠ Skipping API list test (connection dështoi)")
    else:
        results['api_conn'] = False
        results['api_list'] = False
        print("\n⚠ Skipping API tests (env vars mungojnë)")
    
    results['db_conn'] = test_db_connection()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 PËRMBLEDHJE")
    print("=" * 80)
    print()
    
    all_tests = [
        ('Environment Variables', results['env']),
        ('API Connection', results['api_conn']),
        ('API List Invoices', results['api_list']),
        ('Database Connection', results['db_conn']),
    ]
    
    passed = sum(1 for _, result in all_tests if result is True)
    failed = sum(1 for _, result in all_tests if result is False)
    skipped = sum(1 for _, result in all_tests if result is None)
    
    for name, result in all_tests:
        if result is True:
            status = "✓ PASS"
            color = '\033[92m'  # Green
        elif result is False:
            status = "✗ FAIL"
            color = '\033[91m'  # Red
        else:
            status = "⚠ SKIP"
            color = '\033[93m'  # Yellow
        
        reset = '\033[0m'
        print(f"  {color}{status}{reset}  {name}")
    
    print()
    print(f"Total: {len(all_tests)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print()
    
    if failed == 0 and passed > 0:
        print("🎉 GATI PËR PËRDORIM!")
        print()
        print("Hapi tjetër:")
        print("  python app/fetch_all_invoices.py --from 2025-11-01 --to 2025-11-18 --auto-import --dry-run")
        exit_code = 0
    elif failed > 0:
        print("⚠️  DISA TESTE DËSHTUAN")
        print()
        print("Zgjidhje:")
        if not results['env']:
            print("  1. Ekzekuto: .\\setup_efaktura.ps1")
        if not results['api_conn'] or not results['api_list']:
            print("  2. Kontrollo API key dhe URL-të")
        if results['db_conn'] is False:
            print("  3. Kontrollo DB credentials dhe connection")
        exit_code = 1
    else:
        print("⚠️  ASNJË TEST NUK U EKZEKUTUA")
        exit_code = 1
    
    print()
    print("=" * 80)
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
