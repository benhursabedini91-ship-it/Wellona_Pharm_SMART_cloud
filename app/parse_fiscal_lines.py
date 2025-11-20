"""
Parse Fiscal Bill Lines - Nxjerr artikujt (items) nga FB_*.json dhe krijon CSV me rreshta.

Output: staging/fiscal_bills/fiscal_lines_<timestamp>.csv
Kolonat: fiscalBillNumber, lineNo, sku, description, qty, unitPrice, totalLine, taxRate
"""
import os
import sys
import json
import glob
import datetime as dt
from typing import List, Dict, Any

STAGING_DIR = os.path.join(os.path.dirname(__file__), 'staging', 'fiscal_bills')
OUTPUT_CSV = os.path.join(STAGING_DIR, f"fiscal_lines_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")


def extract_lines_from_json(data: Dict[Any, Any], bill_number: str) -> List[Dict]:
    """
    Ekstrakton rreshtat e artikujve nga JSON-i i një fature fiskale.
    Provo fusha të mundshme: items, Items, lines, Lines, invoiceLines, etc.
    """
    lines = []
    
    # Provo disa variante të emrave të fushave
    items_key = None
    for k in ('items', 'Items', 'lines', 'Lines', 'invoiceLines', 'InvoiceLines'):
        if k in data and isinstance(data[k], list):
            items_key = k
            break
    
    if not items_key:
        return []
    
    for idx, item in enumerate(data[items_key], start=1):
        line = {
            'fiscalBillNumber': bill_number,
            'lineNo': idx,
            'sku': '',
            'description': '',
            'qty': None,
            'unitPrice': None,
            'totalLine': None,
            'taxRate': None,
        }
        
        # Provo fusha të mundshme për SKU / barcode
        for k in ('sku', 'SKU', 'itemCode', 'ItemCode', 'barcode', 'Barcode', 'gtin', 'GTIN'):
            if k in item:
                line['sku'] = str(item[k])
                break
        
        # Përshkrim
        for k in ('description', 'Description', 'name', 'Name', 'itemName', 'ItemName'):
            if k in item:
                line['description'] = str(item[k])
                break
        
        # Sasi
        for k in ('qty', 'Qty', 'quantity', 'Quantity'):
            if k in item:
                line['qty'] = item[k]
                break
        
        # Çmim njësi
        for k in ('unitPrice', 'UnitPrice', 'price', 'Price'):
            if k in item:
                line['unitPrice'] = item[k]
                break
        
        # Total linje
        for k in ('totalLine', 'TotalLine', 'lineTotal', 'LineTotal', 'amount', 'Amount'):
            if k in item:
                line['totalLine'] = item[k]
                break
        
        # Tatim (TVSH)
        for k in ('taxRate', 'TaxRate', 'vatRate', 'VatRate'):
            if k in item:
                line['taxRate'] = item[k]
                break
        
        lines.append(line)
    
    return lines


def main():
    pattern = os.path.join(STAGING_DIR, 'FB_*.json')
    files = glob.glob(pattern)
    
    if not files:
        print(f"Asnjë file FB_*.json në {STAGING_DIR}")
        return
    
    all_lines = []
    
    for fpath in files:
        bill_num = os.path.basename(fpath).replace('FB_', '').replace('.json', '')
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            lines = extract_lines_from_json(data, bill_num)
            all_lines.extend(lines)
        except Exception as e:
            print(f"Error parsing {fpath}: {e}")
    
    if not all_lines:
        print("Asnjë rresht i gjetur në JSON files.")
        return
    
    # Shkruaj CSV
    os.makedirs(STAGING_DIR, exist_ok=True)
    with open(OUTPUT_CSV, 'w', encoding='utf-8') as f:
        f.write('fiscalBillNumber;lineNo;sku;description;qty;unitPrice;totalLine;taxRate\n')
        for ln in all_lines:
            f.write(';'.join([
                str(ln['fiscalBillNumber']),
                str(ln['lineNo']),
                str(ln['sku']),
                str(ln['description']),
                str(ln['qty']) if ln['qty'] is not None else '',
                str(ln['unitPrice']) if ln['unitPrice'] is not None else '',
                str(ln['totalLine']) if ln['totalLine'] is not None else '',
                str(ln['taxRate']) if ln['taxRate'] is not None else '',
            ]) + '\n')
    
    print(f"✓ Parsed {len(all_lines)} rreshta nga {len(files)} fatura.")
    print(f"Output: {OUTPUT_CSV}")


if __name__ == '__main__':
    main()
