import os
from dotenv import load_dotenv
from flask import Flask, render_template, abort
from datetime import timezone

from src.db import fetch_all
from src.queries import Q_NODES, Q_LAST_REPORTS, q_disk_metrics_for_reports
from src.utils import now_utc, fmt_bytes, pct, bar_color

load_dotenv()

REFRESH_SECONDS = int(os.getenv("DASH_REFRESH_SECONDS", "5"))
NODE_TIMEOUT_SECONDS = int(os.getenv("NODE_TIMEOUT_SECONDS", "300"))

app = Flask(__name__)

def is_reporting(age_seconds: float | None) -> bool:
    if age_seconds is None:
        return False
    return age_seconds <= NODE_TIMEOUT_SECONDS

@app.route("/")
def index():
    nodes = fetch_all(Q_NODES)
    last_reports = fetch_all(Q_LAST_REPORTS)

    now = now_utc()

    node_to_report = {}
    node_to_age = {}

    for r in last_reports:
        node_to_report[r["node_id"]] = r["report_id"]
        ts = r["server_received_at"]
        # psycopg2 devuelve aware/naive según config; normalizamos
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        node_to_age[r["node_id"]] = (now - ts).total_seconds()

    report_ids = list(node_to_report.values())
    dm_last = []
    if report_ids:
        dm_last = fetch_all(q_disk_metrics_for_reports(len(report_ids)), report_ids)

    # sumar por nodo (último reporte)
    node_cards = []
    summary_total = summary_used = summary_free = 0
    summary_disks = 0
    reporting_count = 0

    # index dm por report_id
    dm_by_report = {}
    for d in dm_last:
        dm_by_report.setdefault(d["report_id"], []).append(d)

    for n in nodes:
        node_id = n["node_id"]
        name = n["node_name"]
        age = node_to_age.get(node_id)
        reporting = is_reporting(age)

        if reporting:
            reporting_count += 1

        rep_id = node_to_report.get(node_id)
        disks = dm_by_report.get(rep_id, []) if rep_id else []

        total = sum(int(x["total_bytes"] or 0) for x in disks)
        used = sum(int(x["used_bytes"] or 0) for x in disks)
        free = sum(int(x["free_bytes"] or 0) for x in disks)
        disk_count = len(disks)

        if reporting:
            summary_total += total
            summary_used += used
            summary_free += free
            summary_disks += disk_count

        p = pct(used, total)
        node_cards.append({
            "node_id": node_id,
            "node_name": name,
            "reporting": reporting,
            "disk_count": disk_count,
            "total": total,
            "used": used,
            "free": free,
            "pct": p,
            "color": bar_color(p),
        })

    summary_pct = pct(summary_used, summary_total)

    return render_template(
        "index.html",
        refresh_seconds=REFRESH_SECONDS,
        node_timeout=NODE_TIMEOUT_SECONDS,
        nodes=node_cards,
        reporting_count=reporting_count,
        total_nodes=len(nodes),
        summary_total=summary_total,
        summary_used=summary_used,
        summary_free=summary_free,
        summary_pct=summary_pct,
        summary_disks=summary_disks,
        fmt_bytes=fmt_bytes
    )

@app.route("/node/<node_id>")
def node_detail(node_id: str):
    # validar si existe el nodo
    node = fetch_all("select node_id, coalesce(node_name, node_id) as node_name from nodes where node_id=%s", [node_id])
    if not node:
        abort(404)
    node = node[0]

    # último reporte
    last = fetch_all("""
        select id as report_id, server_received_at
        from reports
        where node_id=%s and server_received_at is not null
        order by server_received_at desc
        limit 1
    """, [node_id])

    if not last:
        return render_template("node.html", node=node, has_data=False)

    report_id = last[0]["report_id"]

    disks = fetch_all("""
        select disk_name, disk_type, total_bytes, used_bytes, free_bytes, iops, created_at
        from disk_metrics
        where report_id=%s
        order by disk_name
    """, [report_id])

    # histórico por disco (uso %)
    hist = fetch_all("""
        select r.server_received_at as ts,
               dm.disk_name,
               dm.used_bytes,
               dm.total_bytes
        from reports r
        join disk_metrics dm on dm.report_id = r.id
        where r.node_id=%s and r.server_received_at is not null
        order by r.server_received_at asc
    """, [node_id])

    # agrupar histórico por disk_name
    by_disk = {}
    for h in hist:
        name = h["disk_name"]
        used = float(h["used_bytes"] or 0)
        total = float(h["total_bytes"] or 0)
        p = (used / total * 100.0) if total else 0.0
        ts = h["ts"]
        if ts.tzinfo is None:
            # solo para mostrar
            ts = ts.replace(tzinfo=timezone.utc)
        by_disk.setdefault(name, []).append({"ts": ts.isoformat(), "pct": round(p, 2)})

    return render_template(
        "node.html",
        node=node,
        has_data=True,
        disks=disks,
        by_disk=by_disk,
        fmt_bytes=fmt_bytes
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)