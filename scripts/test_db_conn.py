import psycopg2, os
from dotenv import load_dotenv
load_dotenv(r"C:\Wellona\wphAI\.env")

conn = psycopg2.connect(
    host=os.getenv("WPH_DB_HOST"),
    port=os.getenv("WPH_DB_PORT"),
    dbname=os.getenv("WPH_DB_NAME"),
    user=os.getenv("WPH_DB_USER"),
    password=os.getenv("WPH_DB_PASS")
)
cur = conn.cursor()
cur.execute("SELECT current_database(), current_user, version();")
print(cur.fetchall())
cur.close()
conn.close()
