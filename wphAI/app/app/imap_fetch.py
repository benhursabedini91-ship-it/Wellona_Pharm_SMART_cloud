



































import os, imaplib, email, datetime, re, getpass
from email.header import decode_header

IMAP_HOST = os.environ.get("IMAP_HOST") or input("IMAP host (p.sh. outlook.office365.com): ").strip()
IMAP_USER = os.environ.get("IMAP_USER") or input("IMAP username (email i plotë): ").strip()
IMAP_PASS = os.environ.get("IMAP_PASS") or getpass.getpass("IMAP password: ")

SAVE_SOPH = r"C:\Wellona\wphAI\in\sopharma"
SAVE_VEGA = r"C:\Wellona\wphAI\in\vega"
SENDERS_MAP = {
    "xmlfaktura@lekovit.rs": SAVE_SOPH,
    "xmlfakture@vegadoo.rs": SAVE_VEGA,
}
ALLOW = re.compile(r".*\.(xml|xlsx|zip)$", re.IGNORECASE)
SINCE_DAYS = 7

def decode(s):
    if s is None: return ""
    parts = decode_header(s)
    out = ""
    for txt, enc in parts:
        if isinstance(txt, bytes):
            out += txt.decode(enc or "utf-8", errors="replace")
        else:
            out += txt
    return out

def main():
    since = (datetime.date.today() - datetime.timedelta(days=SINCE_DAYS)).strftime("%d-%b-%Y")
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    M.login(IMAP_USER, IMAP_PASS)
    M.select("INBOX")
    # Merr vetëm mesazhet nga dy dërguesit që na duhen, që nga SINCE
    # Përputhje me IMAP: SINCE dhe FROM veç e veç, pastaj bashkohet në kod
    typ, data = M.search(None, f'(SINCE "{since}")')
    if typ != "OK":
        print("Search failed"); return
    ids = data[0].split()
    saved = 0
    for mid in reversed(ids):  # nga më të fundit
        typ, msgdata = M.fetch(mid, "(RFC822)")
        if typ != "OK": continue
        msg = email.message_from_bytes(msgdata[0][1])
        frm = decode(msg.get("From","")).lower()
        # gjej adresën e pastër
        m = re.search(r"<([^>]+)>", frm)
        addr = (m.group(1) if m else frm).strip()
        if addr not in SENDERS_MAP: 
            continue
        dest_dir = SENDERS_MAP[addr]
        # Shkarko vetëm attachment-et e lejuara
        for part in msg.walk():
            if part.get_content_disposition() != "attachment":
                continue
            fname = decode(part.get_filename() or "")
            if not fname or not ALLOW.match(fname):
                continue
            os.makedirs(dest_dir, exist_ok=True)
            path = os.path.join(dest_dir, fname)
            with open(path, "wb") as f:
                f.write(part.get_payload(decode=True))
            print(f"[SAVE] {addr} -> {path}")
            saved += 1
    M.close(); M.logout()
    print(f"[DONE] Saved {saved} attachment(s).")

if __name__ == "__main__":
    main()
