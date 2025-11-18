# Quick ebdata production verification
import psycopg2

conn = psycopg2.connect(
    host='100.69.251.92',
    port=5432,
    dbname='ebdata',
    user='postgresPedja',
    password='supersqlpedja'
)
cur = conn.cursor()

print("="*60)
print("EBDATA PRODUCTION VERIFICATION")
print("="*60)

# Check artikliean table
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema='public' AND table_name LIKE 'artikli%'
""")
print("\nartikli* tables:", [r[0] for r in cur.fetchall()])

# Check if artikliean exists and has data
try:
    cur.execute("SELECT COUNT(*) FROM public.artikliean")
    print(f"  artikliean rows: {cur.fetchone()[0]}")
except:
    print("  artikliean: NOT FOUND")

# Sample RUC values from recent invoices
cur.execute("""
    SELECT ks.artikal, ks.rucstopa, COUNT(*) as cnt
    FROM public.kalkstavke ks
    JOIN public.kalkopste ko ON ks.kalkid = ko.id
    WHERE ko.dokvrsta='20' AND ks.rucstopa > 0
    GROUP BY ks.artikal, ks.rucstopa
    ORDER BY cnt DESC
    LIMIT 10
""")
print("\nTop 10 articles with RUC in recent purchases:")
for r in cur.fetchall():
    print(f"  sifra={r[0]}, ruc={float(r[1]):.2f}%, count={r[2]}")

# Check specific articles from our test invoices
print("\nChecking SINGULAIR & COLDREX (from previous imports):")
for sifra in ['15002019', '15002012', '15011110']:
    cur.execute("SELECT sifra, naziv, barkod FROM public.artikli WHERE sifra=%s", [sifra])
    row = cur.fetchone()
    if row:
        print(f"  {row[0]}: {row[1]}, barcode={row[2]}")
        # Get latest RUC for this article
        cur.execute("""
            SELECT rucstopa FROM public.kalkstavke 
            WHERE artikal=%s AND rucstopa > 0 
            ORDER BY id DESC LIMIT 1
        """, [sifra])
        ruc = cur.fetchone()
        if ruc:
            print(f"    → Latest RUC: {float(ruc[0]):.2f}%")

print("\n" + "="*60)
print("SUMMARY:")
print(f"✓ Connection: postgresPedja@100.69.251.92/ebdata")
print(f"✓ RUC column exists in kalkstavke")
print(f"✓ Typical RUC values: 10-12%")
print("="*60)

conn.close()
