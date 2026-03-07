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


def _reset_sb():
    global _sb
    _sb = None


def get_nodes() -> dict:
    """Devuelve dict node_id -> fila de la tabla nodes."""
    for attempt in range(2):
        sb = _get_sb()
        if not sb:
            return {}
        try:
            resp = sb.table("nodes").select("*").execute()
            return {r["node_id"]: r for r in (resp.data or [])}
        except Exception as e:
            _reset_sb()
            if attempt == 1:
                raise e
    return {}


def get_latest_report(node_id: str) -> dict | None:
    """Devuelve el reporte mas reciente de un nodo."""
    for attempt in range(2):
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
        except Exception as e:
            _reset_sb()
            if attempt == 1:
                raise e
    return None


def bytes_to_gb(b) -> float:
    if not b:
        return 0.0
    return round(float(b) / BYTES_TO_GB, 2)


def compute_cluster_totals(nodes: dict, reports_cache: dict) -> dict:
    """Calcula totales consolidados del cluster."""
    total = used = free = 0.0
    active = 0

    for node_id, node in nodes.items():
        if node.get("status") != "UP":
            continue
        report = reports_cache.get(node_id)
        if not report:
            continue
        raw = report.get("raw_payload") or {}
        disks = raw.get("disks") or []
        for d in disks:
            total += bytes_to_gb(d.get("total_bytes", 0))
            used  += bytes_to_gb(d.get("used_bytes", 0))
            free  += bytes_to_gb(d.get("free_bytes", 0))
        if disks:
            active += 1

    util = (used / total * 100) if total > 0 else 0.0
    return {
        "total_gb":    round(total, 2),
        "used_gb":     round(used, 2),
        "free_gb":     round(free, 2),
        "util_percent": round(util, 1),
        "active":      active,
    }
