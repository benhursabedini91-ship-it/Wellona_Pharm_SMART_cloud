# file: app/efaktura_client.py
import os
import datetime as dt
import re
from typing import List, Dict, Optional, Tuple

try:
    import requests
except Exception:
    requests = None

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

class EFakturaError(Exception):
    pass

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default

# Config via env vars (no secrets in code)
API_BASE = _env('WPH_EFAKT_API_BASE')  # e.g. https://efaktura.mfin.gov.rs
API_KEY = _env('WPH_EFAKT_API_KEY') or _env('WPH_SERBIA_API_KEY')
# Optional explicit endpoints to avoid guessing
LIST_URL = _env('WPH_EFAKT_LIST_URL')  # e.g. https://.../api/.../invoices/received?from=YYYY-MM-DD&to=YYYY-MM-DD
GET_URL = _env('WPH_EFAKT_GET_XML_URL')  # e.g. https://.../api/.../invoices/{invoiceId}/xml

DEFAULT_USER_AGENT = 'wphAI-efaktura/1.0'
SALES_STATUSES = [
    'Draft', 'New', 'Seen', 'Approved', 'Rejected', 'Cancelled', 'Storno'
]
# NOTE: Swagger shows path segment 'efiscalization' (not 'efiskalization').
# Corrected base for fiscal (retail) bills endpoints:
FISCAL_BASE = 'https://efaktura.mfin.gov.rs/api/publicApi/efiscalization/sales'


def _require_requests():
    if requests is None:
        raise EFakturaError('requests library not installed. pip install requests')


def make_session() -> 'requests.Session':
    _require_requests()
    if not API_KEY:
        raise EFakturaError('Missing API key. Set WPH_EFAKT_API_KEY in environment.')
    s = requests.Session()
    s.headers.update({
        'Accept': '*/*',
        'User-Agent': DEFAULT_USER_AGENT,
        'ApiKey': API_KEY,  # Serbia eFaktura uses 'ApiKey' header
    })
    return s


def list_incoming_invoices(s: 'requests.Session', date_from: dt.date, date_to: dt.date, fetch_details: bool = False) -> List[Dict]:
    """
    Returns a list of dicts with at least: id, supplier, invoice_no, issue_date.
    Uses POST /api/publicApi/purchase-invoice/ids to get invoice IDs.
    
    Args:
        fetch_details: If True, fetches overview for each invoice (slower but has supplier info)
                      If False, returns only IDs (faster)
    """
    # Serbia eFaktura uses POST for listing with JSON body
    url = LIST_URL or 'https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/ids'
    
    # POST body with date range
    payload = {
        'dateFrom': date_from.isoformat(),
        'dateTo': date_to.isoformat()
    }
    
    r = s.post(url, json=payload, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'List invoices failed: {r.status_code} {r.text[:300]}')
    
    data = r.json()
    
    # Response is dict with 'PurchaseInvoiceIds' array
    invoice_ids = []
    if isinstance(data, dict):
        invoice_ids = data.get('PurchaseInvoiceIds', [])
    elif isinstance(data, list):
        invoice_ids = data
    
    # Option 1: Fast - return only IDs
    if not fetch_details:
        return [{'id': inv_id, 'supplier': '', 'invoice_no': '', 'issue_date': None} 
                for inv_id in invoice_ids]
    
    # Option 2: Slow - get overview for each ID to get supplier info
    items = []
    for invoice_id in invoice_ids:
        try:
            overview = get_invoice_overview(s, invoice_id)
            items.append({
                'id': invoice_id,
                'supplier': overview.get('supplierName', ''),
                'invoice_no': overview.get('invoiceNumber', ''),
                'issue_date': overview.get('invoiceDate', None),
            })
        except Exception as e:
            # If overview fails, still include the ID
            items.append({
                'id': invoice_id,
                'supplier': '',
                'invoice_no': '',
                'issue_date': None,
            })
    
    return items


def get_invoice_overview(s: 'requests.Session', invoice_id: int) -> Dict:
    """Get invoice overview with supplier info."""
    url = 'https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/overview'
    params = {'invoiceId': invoice_id}
    r = s.get(url, params=params, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'Get overview failed for id={invoice_id}: {r.status_code} {r.text[:300]}')
    return r.json()


def download_invoice_xml(s: 'requests.Session', invoice_id) -> bytes:
    """Download invoice XML using GET /api/publicApi/purchase-invoice/xml"""
    url = GET_URL or 'https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/xml'
    
    # invoiceId as query parameter
    params = {'invoiceId': int(invoice_id)}
    
    r = s.get(url, params=params, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'Download XML failed for id={invoice_id}: {r.status_code} {r.text[:300]}')
    return r.content


def sanitize_filename(name: str) -> str:
    return SAFE_FILENAME_RE.sub('_', name).strip('_')


def save_xml_to_staging(content: bytes, base_dir: Optional[str], supplier: str, invoice_no: str, issue_date: Optional[str], invoice_id: Optional[int] = None) -> str:
    base = base_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'staging', 'faktura_uploads')
    os.makedirs(base, exist_ok=True)
    
    # Use invoice_id if available (most reliable unique identifier)
    if invoice_id:
        fname = f"INV_{invoice_id}.xml"
    else:
        parts = [supplier or 'SUP', invoice_no or 'INV']
        if issue_date:
            parts.append(issue_date)
        fname = sanitize_filename('_'.join(parts)) + '.xml'
    
    fpath = os.path.join(base, fname)
    with open(fpath, 'wb') as f:
        f.write(content)
    return fpath


def fetch_to_staging(date_from: dt.date, date_to: dt.date, base_dir: Optional[str]=None) -> Tuple[int, List[str]]:
    """Fetch incoming invoices from eFaktura and save into staging. Returns (count, paths)."""
    s = make_session()
    got = list_incoming_invoices(s, date_from, date_to)
    saved = []
    for row in got:
        try:
            xml = download_invoice_xml(s, row['id'])
            path = save_xml_to_staging(xml, base_dir, row.get('supplier',''), row.get('invoice_no',''), row.get('issue_date'), row.get('id'))
            saved.append(path)
        except Exception as e:
            # continue on individual download errors
            saved.append(f"ERROR:{row.get('id')}: {e}")
    return (len([p for p in saved if not str(p).startswith('ERROR:')]), saved)


def list_sales_invoice_ids(s: 'requests.Session', date_from: dt.date, date_to: dt.date, status: Optional[str]=None) -> List[int]:
    """Return list of sales invoice IDs using POST /api/publicApi/sales-invoice/ids with query params.

    Args:
        s: requests session
        date_from/date_to: date range (inclusive) as date objects
        status: optional status filter (see SALES_STATUSES)
    """
    url = 'https://efaktura.mfin.gov.rs/api/publicApi/sales-invoice/ids'
    params = {
        'dateFrom': date_from.isoformat(),
        'dateTo': date_to.isoformat()
    }
    if status:
        params['status'] = status
    r = s.post(url, params=params, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'List sales invoices failed: {r.status_code} {r.text[:300]}')
    data = r.json()
    if isinstance(data, dict):
        return data.get('SalesInvoiceIds', []) or data.get('salesInvoiceIds', []) or []
    if isinstance(data, list):
        return data
    return []


def download_sales_invoice_xml(s: 'requests.Session', invoice_id: int) -> bytes:
    """Download sales invoice XML using GET /api/publicApi/sales-invoice/xml"""
    url = 'https://efaktura.mfin.gov.rs/api/publicApi/sales-invoice/xml'
    params = {'invoiceId': int(invoice_id)}
    r = s.get(url, params=params, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'Download sales XML failed for id={invoice_id}: {r.status_code} {r.text[:300]}')
    return r.content


def list_fiscal_bills_for_date(s: 'requests.Session', date_obj: dt.date) -> List[Dict]:
    """Return fiscal bills for a specific date using GET /api/publicApi/efiskalization/sales/fiscal-bill/{dateToGet}.

    Response shape not guaranteed; try JSON parse; fallback to text lines.
    """
    date_str = date_obj.isoformat()
    url = f"{FISCAL_BASE}/fiscal-bill/{date_str}"
    r = s.get(url, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'List fiscal bills failed {r.status_code} {r.text[:300]}')
    try:
        data = r.json()
    except Exception:
        txt = r.text.strip()
        if not txt:
            return []
        return [{'raw': line} for line in txt.splitlines()]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        bills = data.get('fiscalBills') or data.get('FiscalBills') or data.get('items')
        if bills is None:
            return [data]
        return bills
    return []


def get_fiscal_bill(s: 'requests.Session', fiscal_bill_number: str) -> Dict:
    """Get single fiscal bill details by number using GET /api/publicApi/efiskalization/sales/fiscal-bill/{fiscalBillNumber}."""
    num = str(fiscal_bill_number).strip()
    url = f"{FISCAL_BASE}/fiscal-bill/{num}"
    r = s.get(url, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'Get fiscal bill failed {num} {r.status_code} {r.text[:300]}')
    try:
        return r.json()
    except Exception:
        return {'raw': r.text}
