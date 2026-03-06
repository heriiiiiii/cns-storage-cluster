"""
data.py
Funciones de lectura desde Supabase para el dashboard.
Fuente de datos: Supabase (tablas nodes, reports, disk_metrics).
"""

from __future__ import annotations

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

BYTES_TO_GB = 1024 ** 3

_sb: Client | None = None


def _get_sb() -> Client | None:
    global _sb
    if _sb is None and SUPABASE_URL and SUPABASE_KEY:
        _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _sb


def is_connected() -> bool:
    return _get_sb() is not None


def get_nodes() -> dict:
    """Devuelve dict node_id -> fila de la tabla nodes."""
    sb = _get_sb()
    if not sb:
        return {}

    try:
        resp = sb.table("nodes").select("*").execute()
        return {r["node_id"]: r for r in (resp.data or [])}
    except Exception:
        return {}


def get_latest_report(node_id: str) -> dict | None:
    """Devuelve el reporte más reciente de un nodo."""
    sb = _get_sb()
    if not sb:
        return None

    try:
        resp = (
            sb.table("reports")
            .select("*")
            .eq("node_id", node_id)
            .order("server_received_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None


def get_reports_history(node_id: str, start_date=None, end_date=None) -> list[dict]:
    """
    Devuelve el historial de reportes de un nodo, ordenado por fecha ascendente.

    start_date y end_date pueden venir como:
    - datetime.date
    - str
    - o None
    """
    sb = _get_sb()
    if not sb:
        return []

    try:
        query = (
            sb.table("reports")
            .select("*")
            .eq("node_id", node_id)
            .order("server_received_at", desc=False)
        )

        if start_date:
            query = query.gte("server_received_at", str(start_date))
        if end_date:
            # Para incluir todo el día final
            query = query.lte("server_received_at", f"{str(end_date)} 23:59:59")

        resp = query.execute()
        return resp.data or []
    except Exception:
        return []


def bytes_to_gb(b) -> float:
    if not b:
        return 0.0
    return round(float(b) / BYTES_TO_GB, 2)


def normalize_disks_from_payload(raw_payload: dict) -> list[dict]:
    """
    Normaliza el payload para soportar dos formatos:

    Formato 1:
    {
      "disks": [
        {
          "disk_name": "C:\\",
          "total_bytes": ...,
          ...
        }
      ]
    }

    Formato 2:
    {
      "disk_name": "C:\\",
      "total_bytes": ...,
      "used_bytes": ...,
      ...
    }
    """
    raw = raw_payload or {}

    if isinstance(raw.get("disks"), list) and raw.get("disks"):
        return raw.get("disks", [])

    if raw.get("total_bytes") is not None:
        return [raw]

    return []


def extract_report_totals(report: dict | None) -> dict:
    """
    Extrae totales de un reporte y devuelve:
    {
        total_gb,
        used_gb,
        free_gb,
        util_percent,
        disk_count
    }
    """
    if not report:
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "util_percent": 0.0,
            "disk_count": 0,
        }

    raw = report.get("raw_payload") or {}
    disks = normalize_disks_from_payload(raw)

    total = 0.0
    used = 0.0
    free = 0.0

    for d in disks:
        total += bytes_to_gb(d.get("total_bytes", 0))
        used += bytes_to_gb(d.get("used_bytes", 0))
        free += bytes_to_gb(d.get("free_bytes", 0))

    util = (used / total * 100) if total > 0 else 0.0

    return {
        "total_gb": round(total, 2),
        "used_gb": round(used, 2),
        "free_gb": round(free, 2),
        "util_percent": round(util, 2),
        "disk_count": len(disks),
    }


def compute_cluster_totals(nodes: dict, reports_cache: dict) -> dict:
    """Calcula totales consolidados del cluster."""
    total = 0.0
    used = 0.0
    free = 0.0
    active = 0

    for node_id, node in nodes.items():
        if node.get("status") != "UP":
            continue

        report = reports_cache.get(node_id)
        if not report:
            continue

        info = extract_report_totals(report)

        total += info["total_gb"]
        used += info["used_gb"]
        free += info["free_gb"]

        if info["disk_count"] > 0:
            active += 1

    util = (used / total * 100) if total > 0 else 0.0

    return {
        "total_gb": round(total, 2),
        "used_gb": round(used, 2),
        "free_gb": round(free, 2),
        "util_percent": round(util, 1),
        "active": active,
    }