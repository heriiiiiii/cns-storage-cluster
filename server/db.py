# db.py
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# ✅ Carga SIEMPRE el .env del folder server/
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ✅ Modo seguro: si no hay env, no revienta el server
sb = None
if SUPABASE_URL and SUPABASE_KEY:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("[DB] Supabase deshabilitado: falta SUPABASE_URL o SUPABASE_KEY en server/.env")


def insert_report(node_id: str, client_reported_at: str | None, server_received_at: str,
                  interval_seconds: int | None, raw_payload: dict):
    if sb is None:
        return None
    data = {
        "node_id": node_id,
        "client_reported_at": client_reported_at,
        "server_received_at": server_received_at,
        "interval_seconds": interval_seconds,
        "raw_payload": raw_payload,
    }
    return sb.table("reports").insert(data).execute()


def upsert_node(node_id: str, status: str, last_seen: str, addr: str | None, node_name: str | None = None):
    if sb is None:
        return None

    data = {
        "node_id": node_id,
        "status": status,
        "last_seen": last_seen,
        "addr": addr,
    }
    if node_name:
        data["node_name"] = node_name

    # ✅ clave: indicar la columna de conflicto
    return sb.table("nodes").upsert(data, on_conflict="node_id").execute()

def insert_disk_metrics(report_id: str, disks: list):
    """Inserta una fila en disk_metrics por cada disco del reporte."""
    if sb is None or not disks:
        return
    for disk in disks:
        try:
            sb.table("disk_metrics").insert({
                "report_id": report_id,
                "disk_name": disk.get("disk_name"),
                "disk_type": disk.get("disk_type"),
                "total_bytes": disk.get("total_bytes"),
                "used_bytes": disk.get("used_bytes"),
                "free_bytes": disk.get("free_bytes"),
                "iops": disk.get("iops"),
            }).execute()
        except Exception as e:
            print(f"[DB] Error insert disk_metrics: {e}")
