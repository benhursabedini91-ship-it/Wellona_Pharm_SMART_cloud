"""
Check total invoice count by testing different date ranges.
eFaktura API returns max 50 invoices per request.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import make_session, list_incoming_invoices
from datetime import date

def count_by_year(year):
    """Count invoices for a specific year."""
    s = make_session()
    date_from = date(year, 1, 1)
    date_to = date(year, 12, 31)
    
    invoices = list_incoming_invoices(s, date_from, date_to)
    print(f"\n{year}: {len(invoices)} faktura")
    
    if len(invoices) >= 50:
        print(f"  ⚠️  LIMIT! API-ja kthen max 50, mund të ketë më shumë!")
    
    return invoices

def count_by_month(year, month):
    """Count invoices for specific month."""
    s = make_session()
    
    if month == 12:
        next_month_year = year + 1
        next_month = 1
    else:
        next_month_year = year
        next_month = month + 1
    
    date_from = date(year, month, 1)
    date_to = date(next_month_year, next_month, 1)
    
    invoices = list_incoming_invoices(s, date_from, date_to)
    month_name = ["Jan","Feb","Mar","Apr","Maj","Qer","Kor","Gus","Sht","Tet","Nën","Dhj"][month-1]
    print(f"  {month_name} {year}: {len(invoices)} faktura", end="")
    
    if len(invoices) >= 50:
        print(" ⚠️  LIMIT!")
    else:
        print()
    
    return invoices

if __name__ == "__main__":
    print("=" * 60)
    print("  NUMËRIMI I FAKTURAVE - eFaktura")
    print("=" * 60)
    
    # Check 2024
    print("\n📊 VITI 2024:")
    inv_2024 = count_by_year(2024)
    
    # Check 2025
    print("\n📊 VITI 2025:")
    inv_2025 = count_by_year(2025)
    
    # If hit limit, check month-by-month for 2024
    if len(inv_2024) >= 50:
        print("\n🔍 Kontroll mujor për 2024:")
        for m in range(1, 13):
            count_by_month(2024, m)
    
    # Check 2025 month-by-month
    print("\n🔍 Kontroll mujor për 2025:")
    for m in range(1, 12):  # Jan-Nov (December not finished)
        count_by_month(2025, m)
    
    print("\n" + "=" * 60)
    print("PËRFUNDIM:")
    print(f"  Total kërkuar: {len(inv_2024)} (2024) + {len(inv_2025)} (2025)")
    print(f"  Nëse çdo request kthen 50, duhet të ndajmë në periudha më të vogla!")
    print("=" * 60)
