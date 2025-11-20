"""
Import eFaktura registered companies into database.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import psycopg2
import csv
from datetime import datetime

def create_table(conn):
    """Create table for registered companies."""
    cursor = conn.cursor()
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS public.efaktura_registered_companies (
        pib VARCHAR(20) PRIMARY KEY,
        jbkjs VARCHAR(20),
        datum_registracije DATE,
        datum_brisanja DATE,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_efaktura_jbkjs ON public.efaktura_registered_companies(jbkjs);
    CREATE INDEX IF NOT EXISTS idx_efaktura_reg_date ON public.efaktura_registered_companies(datum_registracije);
    
    COMMENT ON TABLE public.efaktura_registered_companies IS 'Lista e kompanive të regjistruara në eFaktura (Serbia)';
    """
    
    cursor.execute(create_sql)
    conn.commit()
    cursor.close()
    print("✓ Tabela u krijua/ekziston")

def import_csv(conn, csv_path):
    """Import CSV data."""
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("TRUNCATE TABLE public.efaktura_registered_companies")
    print("✓ Tabela u pastrua")
    
    # Read and import CSV
    imported = 0
    skipped = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            pib = row['PIB'].strip() if row['PIB'] else None
            jbkjs = row[' JBKJS'].strip() if row.get(' JBKJS') else None
            
            if not pib:
                skipped += 1
                continue
            
            # Parse dates
            try:
                datum_reg = datetime.strptime(row[' Datum registracije'].strip(), '%d.%m.%Y').date() if row.get(' Datum registracije', '').strip() else None
            except:
                datum_reg = None
            
            try:
                datum_bris = datetime.strptime(row[' Datum brisanja'].strip(), '%d.%m.%Y').date() if row.get(' Datum brisanja', '').strip() else None
            except:
                datum_bris = None
            
            try:
                cursor.execute(
                    """
                    INSERT INTO public.efaktura_registered_companies 
                    (pib, jbkjs, datum_registracije, datum_brisanja)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (pib) DO UPDATE SET
                        jbkjs = EXCLUDED.jbkjs,
                        datum_registracije = EXCLUDED.datum_registracije,
                        datum_brisanja = EXCLUDED.datum_brisanja
                    """,
                    (pib, jbkjs, datum_reg, datum_bris)
                )
                imported += 1
                
                if imported % 10000 == 0:
                    print(f"  {imported:,} rreshta importuar...")
                    conn.commit()
                    
            except Exception as e:
                print(f"⚠️  Error importing PIB {pib}: {e}")
                skipped += 1
    
    conn.commit()
    cursor.close()
    
    return imported, skipped

if __name__ == "__main__":
    print("=" * 80)
    print("  eFAKTURA REGISTERED COMPANIES IMPORT")
    print("=" * 80)
    
    # DB connection
    password = os.getenv('WPH_DB_PASS')
    if not password:
        from getpass import getpass
        password = getpass("DB Password: ")
    
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'wph_ai',
        'user': 'smart_pedja',
        'password': password,
        'application_name': 'eFaktura_CompanyImport'
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        print(f"✓ Connected to DB: {conn_params['dbname']}\n")
        
        # Create table
        create_table(conn)
        
        # Import CSV
        csv_path = '../staging/efaktura_registered_companies.csv'
        print(f"\n📂 Importing from: {csv_path}")
        
        imported, skipped = import_csv(conn, csv_path)
        
        # Summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), COUNT(DISTINCT jbkjs) FROM public.efaktura_registered_companies")
        total, unique_jbkjs = cursor.fetchone()
        cursor.close()
        
        print("\n" + "=" * 80)
        print("  PËRFUNDIM")
        print("=" * 80)
        print(f"✓ Importuar: {imported:,} kompani")
        print(f"⚠️  Anashkaluar: {skipped:,}")
        print(f"📊 Total në DB: {total:,}")
        print(f"📊 JBKJS unikë: {unique_jbkjs:,}")
        print("=" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
