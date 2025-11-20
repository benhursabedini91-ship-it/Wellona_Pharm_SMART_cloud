"""
Shkarkues për SALES (dalëse) fakturat nga eFaktura.

Përdorimi:
  $env:WPH_EFAKT_API_KEY="..."
  python fetch_all_sales_invoices.py --from 2025-11-01 --to 2025-11-18 --status Approved --download-xml

Kufizime:
  - Endpoint /sales-invoice/ids kthen MAX 50 ID
  - Nëse lista bosh: nuk ka faktura të shitjes në periudhë
"""
import os, sys
from datetime import datetime, date
import argparse
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from efaktura_client import (
    make_session,
    list_sales_invoice_ids,
    download_sales_invoice_xml,
    save_xml_to_staging,
    SALES_STATUSES,
    EFakturaError
)

def parse_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def main():
    ap = argparse.ArgumentParser(description='Listo dhe (opsionalisht) shkarko SALES faktura (dalëse).')
    ap.add_argument('--from', dest='date_from', required=True)
    ap.add_argument('--to', dest='date_to', required=True)
    ap.add_argument('--status', dest='status', help='Filtro sipas statusit (Draft, New, Seen, Approved, Rejected, Cancelled, Storno)')
    ap.add_argument('--download-xml', action='store_true', help='Shkarko XML për çdo fakturë')
    ap.add_argument('--delay', type=float, default=0.4, help='Delay midis shkarkimeve (rate limit protection)')
    ap.add_argument('--outdir', help='Direktoria e output (default staging/faktura_uploads_sales)')
    args = ap.parse_args()

    if args.status and args.status not in SALES_STATUSES:
        print(f"❌ Status i panjohur: {args.status}. Lejuar: {', '.join(SALES_STATUSES)}")
        sys.exit(1)

    if not os.getenv('WPH_EFAKT_API_KEY'):
        print('❌ Vendos $env:WPH_EFAKT_API_KEY para ekzekutimit.')
        sys.exit(1)

    d_from = parse_date(args.date_from)
    d_to = parse_date(args.date_to)

    print('='*80)
    print('  SALES INVOICE FETCHER')
    print('='*80)
    print(f'Periudha: {d_from} -> {d_to}')
    print(f'Status filter: {args.status or 'ANY'}')
    print(f'Download XML: {args.download_xml}')
    print('='*80)

    try:
        s = make_session()
        ids = list_sales_invoice_ids(s, d_from, d_to, status=args.status)
        print(f"✓ U kthyen {len(ids)} ID")
        if not ids:
            print('⚠️ Nuk ka faktura të shitjes në këtë periudhë ose nuk keni krijuar sales invoices.')
            print('\nArsyet e mundshme:')
            print('  - Nuk keni dorëzuar asnjë sales invoice (dalëse) në eFaktura.')
            print('  - Po shikoni interval shumë të gjerë historik pa të dhëna.')
            print('  - Përdoruesi ka vetëm rol për purchase (hyrëse).')
            print('  - Status filter shumë restriktiv.')
            print('\nProvo:')
            print('  python fetch_all_sales_invoices.py --from 2025-11-15 --to 2025-11-18')
            print('  python fetch_all_sales_invoices.py --from 2025-10-01 --to 2025-11-18 --status Approved')
            return

        if not args.download_xml:
            print('\nID-të e para (max 10):')
            for i in ids[:10]:
                print('  -', i)
            return

        # Download XMLs
        outdir = args.outdir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'staging', 'faktura_uploads_sales')
        os.makedirs(outdir, exist_ok=True)
        print(f'📂 Output: {outdir}')

        successes = 0
        for idx, inv_id in enumerate(ids, 1):
            print(f'[{idx}/{len(ids)}] Shkarkim XML për ID={inv_id}')
            try:
                xml = download_sales_invoice_xml(s, inv_id)
                path = save_xml_to_staging(xml, outdir, 'SALES', f'SALES_{inv_id}', None, inv_id)
                print(f'  ✓ Ruajtur: {os.path.basename(path)}')
                successes += 1
            except Exception as e:
                print(f'  ❌ Gabim: {e}')
            if idx < len(ids):
                time.sleep(args.delay)

        print('\n'+('='*80))
        print('📊 PËRMBLEDHJE:')
        print(f'  Total ID: {len(ids)}')
        print(f'  XML sukses: {successes}')
        print(f'  Dështime: {len(ids)-successes}')

    except EFakturaError as e:
        print(f'❌ EFaktura API gabim: {e}')
    except Exception as e:
        print(f'❌ Gabim i papritur: {e}')

if __name__ == '__main__':
    main()
