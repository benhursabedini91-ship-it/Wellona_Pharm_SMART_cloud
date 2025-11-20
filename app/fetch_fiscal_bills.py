import os
import sys
import json
import datetime as dt
from typing import List, Dict

from efaktura_client import make_session, list_fiscal_bills_for_date, get_fiscal_bill

STAGING_BASE = os.path.join(os.path.dirname(__file__), 'staging', 'fiscal_bills')


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)
    return p


def extract_number(obj: Dict):
    for k in ('fiscalBillNumber', 'billNumber', 'number', 'FiscalBillNumber'):
        v = obj.get(k)
        if v:
            return str(v)
    return None


def run(date: dt.date):
    ensure_dir(STAGING_BASE)
    s = make_session()
    bills = list_fiscal_bills_for_date(s, date)
    if not bills:
        print(f"No fiscal bills returned for {date.isoformat()}")
        return
    header_rows = []
    for b in bills:
        num = extract_number(b) or 'UNKNOWN'
        try:
            full = get_fiscal_bill(s, num)
        except Exception as e:
            full = {'error': str(e), 'number': num}
        out_json = os.path.join(STAGING_BASE, f"FB_{num}.json")
        try:
            with open(out_json, 'w', encoding='utf-8') as f:
                json.dump(full, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Write error {num}: {e}")
        total = None
        issue_dt = None
        item_cnt = None
        # Attempt to extract common fields if present
        for k in ('totalAmount', 'TotalAmount', 'invoiceTotal', 'grandTotal'):
            if k in full:
                total = full[k]
                break
        for k in ('issueDateTime', 'IssueDateTime', 'dateTime', 'createdAt'):
            if k in full:
                issue_dt = full[k]
                break
        for k in ('items', 'Items', 'lines', 'Lines'):
            if k in full and isinstance(full[k], list):
                item_cnt = len(full[k])
                break
        header_rows.append((num, total, issue_dt, item_cnt))
    # summary CSV
    csv_path = os.path.join(STAGING_BASE, f"fiscal_bills_summary_{date.isoformat()}.csv")
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write('fiscalBillNumber;totalAmount;issueDateTime;itemCount\n')
        for r in header_rows:
            f.write(';'.join([str(x) if x is not None else '' for x in r]) + '\n')
    print(f"Saved {len(header_rows)} fiscal bills -> {STAGING_BASE}\nSummary: {csv_path}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            date = dt.date.fromisoformat(sys.argv[1])
        except ValueError:
            print('Date must be YYYY-MM-DD')
            sys.exit(1)
    else:
        date = dt.date.today()
    run(date)
