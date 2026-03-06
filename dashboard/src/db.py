import os
import psycopg2
import psycopg2.extras

def get_conn():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no está configurado en .env")

    # sslmode=require suele ser necesario en Supabase
    return psycopg2.connect(database_url, sslmode="require")

def fetch_all(sql: str, params=None):
    params = params or []
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def fetch_one(sql: str, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None