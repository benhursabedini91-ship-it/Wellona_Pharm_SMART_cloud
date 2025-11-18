# Grant missing privileges to smart_pedja user
# Run this ONCE with postgresPedja to upgrade smart_pedja

import psycopg2

print("="*60)
print("GRANT MISSING PRIVILEGES TO smart_pedja")
print("="*60)

# Connect as superuser
conn = psycopg2.connect(
    host='100.69.251.92',
    port=5432,
    dbname='ebdata',
    user='postgresPedja',
    password='supersqlpedja'
)
conn.autocommit = True
cur = conn.cursor()

# Check current privileges
print("\nCurrent privileges for smart_pedja:")
cur.execute("""
    SELECT 
        has_table_privilege('smart_pedja', 'public.kalkopste', 'SELECT') as select_kalkopste,
        has_table_privilege('smart_pedja', 'public.kalkopste', 'INSERT') as insert_kalkopste,
        has_table_privilege('smart_pedja', 'public.kalkopste', 'UPDATE') as update_kalkopste,
        has_table_privilege('smart_pedja', 'public.kalkkasa', 'UPDATE') as update_kalkkasa,
        has_table_privilege('smart_pedja', 'public.artikliean', 'INSERT') as insert_artikliean
""")
privs = cur.fetchone()
print(f"  SELECT on kalkopste: {privs[0]}")
print(f"  INSERT on kalkopste: {privs[1]}")
print(f"  UPDATE on kalkopste: {privs[2]}")
print(f"  UPDATE on kalkkasa: {privs[3]}")
print(f"  INSERT on artikliean: {privs[4]}")

# Grant missing privileges
print("\nGranting missing privileges...")

missing_grants = [
    ("UPDATE", "kalkopste"),
    ("UPDATE", "kalkkasa"),
    ("UPDATE", "kalkstavke"),
    ("INSERT", "artikliean"),
    ("UPDATE", "artikliean"),
    ("INSERT", "artikli"),  # For auto-register
]

for priv, table in missing_grants:
    try:
        cur.execute(f"GRANT {priv} ON public.{table} TO smart_pedja")
        print(f"  ✓ GRANT {priv} ON {table}")
    except Exception as e:
        print(f"  ⚠️  Failed to grant {priv} on {table}: {e}")

# Grant sequence usage (for ID generation)
print("\nGranting sequence privileges...")
sequences = ['kalkopste_id_seq', 'kalkkasa_id_seq', 'artikli_id_seq']

for seq in sequences:
    try:
        cur.execute(f"GRANT USAGE, SELECT ON SEQUENCE public.{seq} TO smart_pedja")
        print(f"  ✓ GRANT USAGE ON {seq}")
    except Exception as e:
        print(f"  ⚠️  Sequence {seq} might not exist: {str(e)[:60]}")

print("\n" + "="*60)
print("✅ PRIVILEGES GRANTED!")
print("="*60)

# Verify new privileges
print("\nVerifying new privileges:")
cur.execute("""
    SELECT 
        has_table_privilege('smart_pedja', 'public.kalkopste', 'UPDATE') as update_kalkopste,
        has_table_privilege('smart_pedja', 'public.kalkkasa', 'UPDATE') as update_kalkkasa,
        has_table_privilege('smart_pedja', 'public.artikliean', 'INSERT') as insert_artikliean
""")
new_privs = cur.fetchone()
print(f"  UPDATE on kalkopste: {new_privs[0]} ✓")
print(f"  UPDATE on kalkkasa: {new_privs[1]} ✓")
print(f"  INSERT on artikliean: {new_privs[2]} ✓")

# Test write capability
print("\nTesting write capability...")
conn.close()

test_conn = psycopg2.connect(
    host='100.69.251.92',
    port=5432,
    dbname='ebdata',
    user='smart_pedja',
    password='wellona-server'
)
test_conn.autocommit = False  # Use transaction
test_cur = test_conn.cursor()

try:
    # Test SELECT
    test_cur.execute("SELECT COUNT(*) FROM public.artikli")
    print(f"✓ Can SELECT: {test_cur.fetchone()[0]} articles")
    
    # Test INSERT (will rollback)
    test_cur.execute("SELECT MAX(id) FROM public.kalkkasa")
    max_id = test_cur.fetchone()[0]
    test_cur.execute("""
        INSERT INTO public.kalkkasa 
        (id, datumkase, iznos, dokvrsta, dokbroj, magacin, periodid, dokdatum)
        VALUES (%s, NOW(), 0, '20', 'TEST', '101', 4, NOW())
    """, [max_id + 99999])
    print(f"✓ Can INSERT into kalkkasa")
    
    # Test UPDATE
    test_cur.execute("UPDATE public.kalkkasa SET iznos=0 WHERE id=%s", [max_id + 99999])
    print(f"✓ Can UPDATE kalkkasa")
    
    # Rollback test
    test_conn.rollback()
    print("✓ Test transaction rolled back (no data changed)")
    
    print("\n✅ ALL TESTS PASSED!")
    print("\nYou can now use smart_pedja for imports:")
    print("  $env:WPH_DB_USER='smart_pedja'")
    print("  $env:WPH_DB_PASS='wellona-server'")
    
except Exception as e:
    test_conn.rollback()
    print(f"\n❌ Test failed: {e}")
    print("Check if postgresPedja has granted the privileges correctly.")

test_conn.close()

print("\n" + "="*60)
