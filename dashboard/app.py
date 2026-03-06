"""
app.py
Dashboard CNS — Monitor Nacional de Almacenamiento
Ejecutar: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from config import EXPECTED_NODES, SERVER_HOST, SERVER_ADMIN_PORT
from data import (
    is_connected,
    get_nodes,
    get_latest_report,
    bytes_to_gb,
    compute_cluster_totals,
)

st.set_page_config(
    page_title="CNS Storage Dashboard",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuración")

    refresh_interval = st.selectbox(
        "Auto-refresco",
        [5, 10, 30, 60],
        index=1,
        format_func=lambda x: f"{x}s",
    )
    paused = st.checkbox("Pausar refresco", value=False)

    if not paused:
        st_autorefresh(interval=refresh_interval * 1000, key="autorefresh")

    st.divider()

    if is_connected():
        st.success("✅ Supabase conectado")
    else:
        st.error("❌ Sin conexión a Supabase")

    st.caption(f"Actualizado: {datetime.now().strftime('%H:%M:%S')}")


# ─── Cargar datos ─────────────────────────────────────────────────────────
nodes: dict = {}
reports_cache: dict = {}
load_error: str | None = None

try:
    nodes = get_nodes()
    for node_id in EXPECTED_NODES:
        r = get_latest_report(node_id)
        if r:
            reports_cache[node_id] = r
except Exception as e:
    load_error = str(e)


# ─── Header ───────────────────────────────────────────────────────────────
st.title("🗄️ CNS — Monitor Nacional de Almacenamiento")

if load_error:
    st.error(f"❌ Error al obtener datos: {load_error}")
    st.stop()

if not nodes and not reports_cache:
    st.info("⏳ Esperando reportes de los nodos...")
    st.stop()


# ─── Sección 1: Totales del Cluster ───────────────────────────────────────
st.subheader("📊 Totales del Cluster")

totals = compute_cluster_totals(nodes, reports_cache)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Capacidad Total",  f"{totals['total_gb']:.1f} GB")
c2.metric("Usado",            f"{totals['used_gb']:.1f} GB")
c3.metric("Libre",            f"{totals['free_gb']:.1f} GB")
c4.metric("Utilización",      f"{totals['util_percent']:.1f}%")
c5.metric("Nodos activos",    f"{totals['active']} / {len(EXPECTED_NODES)}")

st.divider()


# ─── Sección 2: Lista de Nodos ────────────────────────────────────────────
st.subheader("🖥️ Estado de Nodos")

table_rows = []
for node_id in EXPECTED_NODES:
    node   = nodes.get(node_id, {})
    report = reports_cache.get(node_id)

    status    = node.get("status", "SIN DATOS")
    last_seen = node.get("last_seen", "—")

    disk_summary = "—"
    util_pct     = "—"

    if report:
        raw   = report.get("raw_payload") or {}
        disks = raw.get("disks") or []
        if disks:
            total = sum(bytes_to_gb(d.get("total_bytes", 0)) for d in disks)
            used  = sum(bytes_to_gb(d.get("used_bytes",  0)) for d in disks)
            pct   = (used / total * 100) if total > 0 else 0.0
            disk_summary = f"{used:.1f} / {total:.1f} GB"
            util_pct     = f"{pct:.1f}%"

    status_icon = "🟢" if status == "UP" else "🔴"
    table_rows.append({
        "Estado":              f"{status_icon} {status}",
        "Nodo":                node_id,
        "Último reporte (UTC)": last_seen,
        "Uso disco":           disk_summary,
        "% Uso":               util_pct,
    })

st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

st.divider()


# ─── Sección 3: Detalle de Nodo ───────────────────────────────────────────
st.subheader("🔍 Detalle de Nodo")

selected_node = st.selectbox("Seleccionar nodo", EXPECTED_NODES, key="selected_node")
report = reports_cache.get(selected_node)

if not report:
    st.warning(f"⏳ Sin datos disponibles para **{selected_node}**.")
else:
    raw   = report.get("raw_payload") or {}
    disks = raw.get("disks") or []
    extra = raw.get("extra") or {}

    col_ts, col_extra = st.columns(2)

    with col_ts:
        st.markdown("**⏱️ Timestamps del reporte**")
        st.text(f"Reportado por cliente : {report.get('client_reported_at', '—')}")
        st.text(f"Recibido por servidor  : {report.get('server_received_at', '—')}")
        st.text(f"Intervalo configurado  : {report.get('interval_seconds', '—')}s")

    with col_extra:
        st.markdown("**🌐 Datos extra del nodo**")
        st.text(f"IP  : {extra.get('ip')  or 'No disponible'}")
        st.text(f"MAC : {extra.get('mac') or 'No disponible'}")
        ram_total = bytes_to_gb(extra.get("ram_total_bytes"))
        ram_used  = bytes_to_gb(extra.get("ram_used_bytes"))
        if ram_total:
            st.text(f"RAM : {ram_used:.1f} / {ram_total:.1f} GB")
        else:
            st.text("RAM : No disponible")

    st.markdown(f"**💾 Discos detectados en {selected_node}**")

    if not disks:
        st.info("Sin datos de discos.")
    else:
        disk_rows = []
        for d in disks:
            total = bytes_to_gb(d.get("total_bytes", 0))
            used  = bytes_to_gb(d.get("used_bytes",  0))
            free  = bytes_to_gb(d.get("free_bytes",  0))
            pct   = (used / total * 100) if total > 0 else 0.0
            iops  = d.get("iops")
            disk_rows.append({
                "Dispositivo": d.get("disk_name", "—"),
                "Tipo":        d.get("disk_type", "—"),
                "Total (GB)":  f"{total:.1f}",
                "Usado (GB)":  f"{used:.1f}",
                "Libre (GB)":  f"{free:.1f}",
                "% Uso":       f"{pct:.1f}%",
                "IOPS":        f"{int(iops):,}" if iops else "—",
            })
        st.dataframe(pd.DataFrame(disk_rows), use_container_width=True, hide_index=True)

st.divider()


# ─── Sección 4: Enviar Comando ────────────────────────────────────────────
st.subheader("📨 Enviar Comando a Nodo")

cmd_col1, cmd_col2 = st.columns([1, 2])
with cmd_col1:
    cmd_node = st.selectbox("Nodo destino", EXPECTED_NODES, key="cmd_node")
with cmd_col2:
    cmd_text = st.text_input("Comando", placeholder="ej: ping, reiniciar_servicio")

if st.button("Enviar comando", type="primary"):
    if not cmd_text.strip():
        st.warning("Escribe un comando antes de enviar.")
    else:
        try:
            resp = requests.post(
                f"http://{SERVER_HOST}:{SERVER_ADMIN_PORT}/command",
                json={"node_id": cmd_node, "command": cmd_text.strip()},
                timeout=5,
            )
            if resp.status_code == 200:
                st.success(f"✅ Comando enviado a **{cmd_node}**: `{cmd_text}`")
            else:
                st.error(f"Error del servidor: {resp.text}")
        except Exception as e:
            st.error(f"No se pudo contactar el servidor admin ({SERVER_HOST}:{SERVER_ADMIN_PORT}): {e}")
