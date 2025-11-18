import os, psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

def get_conn():
    return psycopg2.connect(
        host=os.getenv("WPH_DB_HOST","127.0.0.1"),
        port=int(os.getenv("WPH_DB_PORT","5432")),
        dbname=os.getenv("WPH_DB_NAME","wph_ai"),
        user=os.getenv("WPH_DB_USER","postgres"),
        password=os.getenv("WPH_DB_PASS","")
    )

def fetch_all(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
