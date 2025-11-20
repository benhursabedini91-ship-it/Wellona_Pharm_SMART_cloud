"""
Fiscal Bill Alarm - Kontrollon nëse ka 2+ ditë me radhë pa fatura fiskale (Count=0).
Nëse po → shkruan në logs/fiscal_alarm.log dhe mund të dërgojë email.
"""
import os
import sys
import datetime as dt
from typing import List, Tuple

from efaktura_client import make_session, list_fiscal_bills_for_date

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
ALARM_LOG = os.path.join(LOGS_DIR, 'fiscal_alarm.log')
THRESHOLD_DAYS = 2  # Sa ditë me radhë pa fatura duhet që të aktivizohet alarmi


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def check_recent_days(days_back: int = 7) -> List[Tuple[dt.date, int]]:
    """
    Kontrollon N ditët e fundit dhe kthen listë (date, count).
    """
    s = make_session()
    results = []
    today = dt.date.today()
    for i in range(days_back):
        d = today - dt.timedelta(days=i)
        try:
            bills = list_fiscal_bills_for_date(s, d)
            count = len(bills)
        except Exception as e:
            # Nëse ka error API, shëno si -1
            count = -1
        results.append((d, count))
    return results


def find_consecutive_zeros(history: List[Tuple[dt.date, int]]) -> int:
    """
    Llogarit sa ditë me radhë (duke filluar nga data më e re) kanë count=0.
    """
    consecutive = 0
    for date, count in history:
        if count == 0:
            consecutive += 1
        else:
            break
    return consecutive


def log_alarm(message: str):
    ensure_dir(LOGS_DIR)
    timestamp = dt.datetime.now().isoformat()
    with open(ALARM_LOG, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"ALARM: {message}")


def send_email_alert(subject: str, body: str):
    """
    Placeholder për email alert. Shto SMTP config këtu nëse dëshiron email automatik.
    """
    # Shembull (jo aktiv):
    # import smtplib
    # from email.mime.text import MIMEText
    # ...
    print(f"[EMAIL PLACEHOLDER] Subject: {subject}")
    print(f"Body: {body}")


def main():
    history = check_recent_days(days_back=7)
    print("Historiku i 7 ditëve të fundit:")
    for date, count in history:
        status = "OK" if count > 0 else ("ERROR API" if count == -1 else "ZERO")
        print(f"  {date.isoformat()}: {count} fatura [{status}]")
    
    consecutive = find_consecutive_zeros(history)
    print(f"\nDitë me radhë pa fatura: {consecutive}")
    
    if consecutive >= THRESHOLD_DAYS:
        msg = f"ALARM: {consecutive} ditë me radhë pa fatura fiskale (threshold={THRESHOLD_DAYS})"
        log_alarm(msg)
        # Opsionale: Dërgo email
        send_email_alert(
            subject="Fiscal Bill Alarm - Zero Invoices",
            body=msg + f"\n\nHistorik:\n" + "\n".join([f"{d}: {c}" for d, c in history])
        )
    else:
        print("✓ Asnjë alarm. Gjendja normale.")


if __name__ == '__main__':
    main()
