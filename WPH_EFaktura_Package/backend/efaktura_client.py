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


def _require_requests():
    if requests is None:
        raise EFakturaError('requests library not installed. pip install requests')


def make_session() -> 'requests.Session':
    _require_requests()
    if not API_KEY:
        raise EFakturaError('Missing API key. Set WPH_EFAKT_API_KEY in environment.')
    s = requests.Session()
    s.headers.update({
        'Accept': 'application/json',
        'User-Agent': DEFAULT_USER_AGENT,
        'x-api-key': API_KEY,  # adjust if API expects Authorization instead
    })
    return s


def list_incoming_invoices(s: 'requests.Session', date_from: dt.date, date_to: dt.date) -> List[Dict]:
    """
    Returns a list of dicts with at least: id, supplier, invoice_no, issue_date.
    Endpoint is provided via WPH_EFAKT_LIST_URL; if not provided, raises with a helpful hint.
    """
    if LIST_URL:
        url = LIST_URL.format(
            fromDate=date_from.isoformat(), toDate=date_to.isoformat()
        )
    else:
        raise EFakturaError(
            'WPH_EFAKT_LIST_URL not set. Provide a full URL with parameters, e.g. '\
            'https://efaktura.../invoices/received?fromDate={fromDate}&toDate={toDate}'
        )
    r = s.get(url, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'List invoices failed: {r.status_code} {r.text[:300]}')
    data = r.json()
    # Normalize minimal fields (adapt mapping here if swagger differs)
    items = []
    for row in data if isinstance(data, list) else data.get('items', []):
        items.append({
            'id': row.get('id') or row.get('uuid') or row.get('invoiceId'),
            'supplier': (row.get('supplierName') or row.get('supplier') or ''),
            'invoice_no': row.get('invoiceNumber') or row.get('number') or '',
            'issue_date': row.get('issueDate') or row.get('date') or None,
        })
    return items


def download_invoice_xml(s: 'requests.Session', invoice_id: str) -> bytes:
    if not GET_URL:
        raise EFakturaError(
            'WPH_EFAKT_GET_XML_URL not set. Provide a URL with {invoiceId} placeholder, e.g. '\
            'https://efaktura.../invoices/{invoiceId}/xml'
        )
    url = GET_URL.format(invoiceId=invoice_id)
    r = s.get(url, timeout=60)
    if r.status_code >= 400:
        raise EFakturaError(f'Download XML failed for id={invoice_id}: {r.status_code} {r.text[:300]}')
    return r.content


def sanitize_filename(name: str) -> str:
    return SAFE_FILENAME_RE.sub('_', name).strip('_')


def save_xml_to_staging(content: bytes, base_dir: Optional[str], supplier: str, invoice_no: str, issue_date: Optional[str]) -> str:
    base = base_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'staging', 'faktura_uploads')
    os.makedirs(base, exist_ok=True)
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
            path = save_xml_to_staging(xml, base_dir, row.get('supplier',''), row.get('invoice_no',''), row.get('issue_date'))
            saved.append(path)
        except Exception as e:
            # continue on individual download errors
            saved.append(f"ERROR:{row.get('id')}: {e}")
    return (len([p for p in saved if not str(p).startswith('ERROR:')]), saved)
