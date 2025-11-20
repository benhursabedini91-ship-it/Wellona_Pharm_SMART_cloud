import os
import sys
import json
from efaktura_client import make_session, get_fiscal_bill

STAGING_BASE = os.path.join(os.path.dirname(__file__), 'staging', 'fiscal_bills')


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)
    return p


def main(num: str):
    ensure_dir(STAGING_BASE)
    s = make_session()
    data = get_fiscal_bill(s, num)
    out_path = os.path.join(STAGING_BASE, f"FB_{num}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Shfaq disa fusha kryesore nqs ekzistojnë
    total = data.get('totalAmount') or data.get('TotalAmount')
    issue_dt = data.get('issueDate') or data.get('IssueDate') or data.get('issueDateTime')
    print(f"Ruajtur JSON: {out_path}")
    print(f"Numri: {num} | Total: {total} | Data: {issue_dt}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Perdorimi: python fetch_fiscal_bill_number.py <fiscalBillNumber>')
        sys.exit(1)
    main(sys.argv[1])
