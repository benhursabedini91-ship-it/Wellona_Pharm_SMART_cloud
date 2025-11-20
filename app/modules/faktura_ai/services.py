# services.py for faktura_ai module
import csv
import io
from datetime import datetime
from decimal import Decimal
import psycopg2
from .sopharma_to_erp import insert_kalkulacija, MP_CONFIG, DB_DEFAULTS

def parse_invoices_csv(file_stream):
    """Parse CSV file with invoice data.
    
    Expected CSV format:
    supplier,invoice_no,invoice_date,item_sifra,item_name,item_qty,item_price,item_rabat_pct
    """
    invoices = {}
    
    reader = csv.DictReader(io.StringIO(file_stream.read().decode('utf-8')))
    
    for row in reader:
        supplier = row.get('supplier', '').strip()
        invoice_no = row.get('invoice_no', '').strip()
        invoice_date_str = row.get('invoice_date', '').strip()
        
        try:
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
        except:
            invoice_date = datetime.now()
        
        item_sifra = row.get('item_sifra', '').strip()
        item_name = row.get('item_name', '').strip()
        item_qty = Decimal(row.get('item_qty', '0').replace(',', '.'))
        item_price = Decimal(row.get('item_price', '0').replace(',', '.'))
        item_rabat_pct = Decimal(row.get('item_rabat_pct', '0').replace(',', '.'))
        
        key = (supplier, invoice_no)
        if key not in invoices:
            invoices[key] = {
                'supplier': supplier,
                'invoice_no': invoice_no,
                'invoice_date': invoice_date,
                'items': []
            }
        
        invoices[key]['items'].append({
            'sifra': item_sifra,
            'naziv': item_name,
            'kolicina': item_qty,
            'cena_fakturna': item_price,
            'rabat_pct': item_rabat_pct,
            'pdv_pct': 10.0,  # Default PDV
            'barcode': None,
            'serija': None,
            'rok_dt': None
        })
    
    return list(invoices.values())

def send_invoices_to_erp(invoices, dry_run=False):
    """Send parsed invoices to ERP database.
    
    Returns summary dict with processed, invoices, errors.
    """
    processed = 0
    total_invoices = len(invoices)
    errors = []
    
    # Database connection
    db_cfg = DB_DEFAULTS.copy()
    if not db_cfg['password']:
        db_cfg['password'] = ''  # Assume env var is set
    
    conn = psycopg2.connect(**db_cfg)
    
    try:
        allow_remote = True  # Allow for this module
        
        for invoice in invoices:
            try:
                # Convert to header/items format expected by insert_kalkulacija
                header = {
                    'broj_faktura': invoice['invoice_no'],
                    'datum': invoice['invoice_date'],
                    'dobavljac': invoice['supplier'],
                    'total_neto': sum(item['kolicina'] * item['cena_fakturna'] * (1 - item['rabat_pct']/100) for item in invoice['items']),
                    'valuta_datum': None,
                    'cash_discount': Decimal('0'),
                    'payable_amount': Decimal('0')
                }
                
                items = invoice['items']
                
                kalk_id = insert_kalkulacija(
                    conn, header, items, MP_CONFIG,
                    dry_run=dry_run,
                    allow_remote_write=allow_remote
                )
                
                if kalk_id:
                    processed += 1
                else:
                    errors.append(f"Failed to insert invoice {invoice['invoice_no']}")
                    
            except Exception as e:
                errors.append(f"Error processing invoice {invoice['invoice_no']}: {str(e)}")
    
    finally:
        conn.close()
    
    return {
        'processed': processed,
        'invoices': total_invoices,
        'errors': len(errors),
        'error_details': errors
    }