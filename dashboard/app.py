"""
app.py
Dashboard CNS — Monitor Nacional de Almacenamiento

Ejecutar:
    python -m streamlit run app.py
"""

from datetime import datetime, date, timedelta

import altair as alt
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False

import data as data_module
from config import EXPECTED_NODES, SERVER_HOST, SERVER_ADMIN_PORT
from data import (
    is_connected,
    get_nodes,
    get_latest_report,
    bytes_to_gb,
    compute_cluster_totals,
)

# =========================================================
# Configuración general
# =========================================================
st.set_page_config(
    page_title="CNS Storage Dashboard",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# CSS / Estilo visual oscuro
# =========================================================
st.markdown("""
<style>
:root {
    --bg: #0e1117;
    --panel: #151a21;
    --panel-2: #1b212b;
    --border: rgba(255,255,255,0.07);
    --text: #eef2f7;
    --muted: #aeb8c5;
    --green: #22c55e;
    --orange: #f59e0b;
    --red: #ef4444;
    --blue: #60a5fa;
    --shadow: 0 10px 24px rgba(0,0,0,0.22);
}

html, body, [class*="css"] {
    font-family: "Segoe UI", Inter, Arial, sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #0b1018 0%, #111827 100%);
}

.block-container {
    max-width: 1500px;
    padding-top: 1.1rem;
    padding-bottom: 1.5rem;
}

.main-title {
    font-size: 2.15rem;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 0.15rem;
}

.sub-title {
    color: var(--muted);
    font-size: 1rem;
    margin-bottom: 1rem;
}

.section-title {
    font-size: 1.3rem;
    font-weight: 800;
    color: var(--text);
    margin: 0.7rem 0 0.8rem 0;
}

.hero-panel {
    background: linear-gradient(135deg, #121822 0%, #192231 100%);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 22px;
    box-shadow: var(--shadow);
    margin-bottom: 16px;
}

.node-card {
    background: linear-gradient(180deg, #171d27 0%, #121821 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 16px;
    box-shadow: var(--shadow);
    min-height: 220px;
    margin-bottom: 14px;
}

.node-card:hover {
    transform: translateY(-2px);
    transition: 0.18s ease;
}

.node-name {
    font-size: 1.12rem;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 6px;
}

.node-status {
    margin-bottom: 10px;
    font-size: 0.9rem;
    font-weight: 700;
}

.node-meta {
    color: var(--muted);
    font-size: 0.93rem;
    margin-bottom: 3px;
}

.progress-wrap {
    margin-top: 14px;
    width: 100%;
    height: 14px;
    background: #3a4351;
    border-radius: 999px;
    overflow: hidden;
}

.progress-fill {
    height: 14px;
    border-radius: 999px;
}

.badge {
    display: inline-block;
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
}

.badge-ok {
    background: rgba(34,197,94,0.18);
    color: #d8ffe5;
    border: 1px solid rgba(34,197,94,0.35);
}

.badge-down {
    background: rgba(239,68,68,0.16);
    color: #ffdcdc;
    border: 1px solid rgba(239,68,68,0.35);
}

.small-note {
    color: var(--muted);
    font-size: 0.82rem;
    margin-top: 8px;
}

[data-testid="stMetric"] {
    background: linear-gradient(180deg, #151b24 0%, #11161e 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 18px;
    padding: 14px;
    box-shadow: var(--shadow);
}

[data-testid="stMetricLabel"] {
    color: var(--muted);
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: var(--text);
    font-weight: 800;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    background: #11161e;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 10px 14px;
    color: var(--text);
}

.stTabs [aria-selected="true"] {
    background: #1a2330 !important;
    border-color: rgba(96,165,250,0.25) !important;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    border-radius: 12px !important;
    background: #11161e !important;
    border-color: rgba(255,255,255,0.08) !important;
    color: var(--text) !important;
}

.stTextInput input,
.stSelectbox div,
.stDateInput input {
    color: var(--text) !important;
}

.stButton > button {
    border-radius: 12px;
    font-weight: 700;
    background: #2563eb;
    color: white;
    border: none;
    padding: 0.55rem 1rem;
}

.stButton > button:hover {
    background: #1d4ed8;
    color: white;
}

.stAlert {
    border-radius: 14px;
}

hr {
    border-color: rgba(255,255,255,0.06);
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# Helpers
# =========================================================
def safe_text(value, default="—"):
    return default if value in (None, "", []) else value


def normalize_disks_from_payload(raw_payload: dict) -> list[dict]:
    raw = raw_payload or {}

    if isinstance(raw.get("disks"), list) and raw.get("disks"):
        return raw["disks"]

    if raw.get("total_bytes") is not None:
        return [raw]

    return []


def sum_disk_usage_gb(disks: list[dict]) -> tuple[float, float, float, float]:
    total_gb = sum(bytes_to_gb(d.get("total_bytes", 0)) for d in disks)
    used_gb = sum(bytes_to_gb(d.get("used_bytes", 0)) for d in disks)
    free_gb = sum(bytes_to_gb(d.get("free_bytes", 0)) for d in disks)
    pct = (used_gb / total_gb * 100) if total_gb > 0 else 0.0
    return total_gb, used_gb, free_gb, pct


def format_status(status: str) -> str:
    if status == "UP":
        return "🟢 UP"
    if status == "NO_REPORTA":
        return "🔴 NO_REPORTA"
    return f"🟡 {safe_text(status, 'SIN DATOS')}"


def get_usage_color(pct: float) -> str:
    if pct >= 85:
        return "#ef4444"
    if pct >= 60:
        return "#f59e0b"
    return "#22c55e"


def load_history(node_id: str, start_date=None, end_date=None):
    history_fn = getattr(data_module, "get_reports_history", None)
    if history_fn is None:
        return None
    return history_fn(node_id, start_date=start_date, end_date=end_date)


def build_history_dataframe(history_reports: list[dict], node_id: str) -> pd.DataFrame:
    rows = []

    for rep in history_reports or []:
        raw = rep.get("raw_payload") or {}
        disks = normalize_disks_from_payload(raw)
        total_gb, used_gb, free_gb, util_pct = sum_disk_usage_gb(disks)

        rows.append({
            "Fecha": rep.get("server_received_at"),
            "Nodo": node_id,
            "Total (GB)": round(total_gb, 2),
            "Usado (GB)": round(used_gb, 2),
            "Libre (GB)": round(free_gb, 2),
            "% Uso": round(util_pct, 2),
            "Reportado cliente": rep.get("client_reported_at"),
            "Intervalo (s)": rep.get("interval_seconds"),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        df = df.sort_values("Fecha").reset_index(drop=True)

    return df


# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.title("⚙️ Configuración")

    refresh_interval = st.selectbox(
        "Auto-refresco",
        [5, 10, 30, 60],
        index=1,
        format_func=lambda x: f"{x}s",
    )
    paused = st.checkbox("Pausar refresco", value=False)

    if HAS_AUTOREFRESH:
        if not paused:
            st_autorefresh(interval=refresh_interval * 1000, key="autorefresh")
    else:
        st.warning("Falta instalar streamlit-autorefresh.")

    st.divider()

    if is_connected():
        st.success("✅ Supabase conectado")
    else:
        st.error("❌ Sin conexión a Supabase")

    st.caption(f"Actualizado: {datetime.now().strftime('%H:%M:%S')}")
    st.caption(f"Servidor admin: {SERVER_HOST}:{SERVER_ADMIN_PORT}")

# =========================================================
# Carga de datos
# =========================================================
nodes: dict = {}
reports_cache: dict = {}
load_error: str | None = None

try:
    nodes = get_nodes() or {}
    for node_id in EXPECTED_NODES:
        latest = get_latest_report(node_id)
        if latest:
            reports_cache[node_id] = latest
except Exception as e:
    load_error = str(e)

# =========================================================
# Header
# =========================================================
st.markdown('<div class="main-title">🗄️ Monitor Nacional de Almacenamiento</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Panel central del cluster para visualización de capacidad, uso de discos, estado por nodo e histórico de reportes.</div>',
    unsafe_allow_html=True,
)

if load_error:
    st.error(f"❌ Error al obtener datos: {load_error}")
    st.stop()

if not nodes and not reports_cache:
    st.info("⏳ Esperando reportes de los nodos...")
    st.stop()

# =========================================================
# Tabs
# =========================================================
tab_resumen, tab_nodos, tab_hist, tab_cmd = st.tabs([
    "📊 Resumen",
    "🖥️ Nodos",
    "📈 Histórico",
    "📨 Comandos",
])

# =========================================================
# TAB 1: RESUMEN
# =========================================================
with tab_resumen:
    totals = compute_cluster_totals(nodes, reports_cache)

    total_disks = 0
    for report in reports_cache.values():
        raw = report.get("raw_payload") or {}
        disks = normalize_disks_from_payload(raw)
        total_disks += len(disks)

    st.markdown('<div class="section-title">Vista general del cluster</div>', unsafe_allow_html=True)

    top_left, top_right = st.columns([3.3, 1.4])

    with top_left:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Capacidad Total", f"{totals['total_gb']:.1f} GB")
        c2.metric("Usado", f"{totals['used_gb']:.1f} GB")
        c3.metric("Libre", f"{totals['free_gb']:.1f} GB")
        c4.metric("Utilización", f"{totals['util_percent']:.1f}%")
        c5.metric("Nodos activos", f"{totals['active']} / {len(EXPECTED_NODES)}")

        info1, info2 = st.columns([1.1, 3])
        with info1:
            st.metric("Discos detectados", f"{total_disks}")
        with info2:
            st.info(
                f"El cluster registra **{total_disks} discos**, con **{totals['used_gb']:.1f} GB usados**, "
                f"**{totals['free_gb']:.1f} GB libres** y una utilización global de **{totals['util_percent']:.1f}%**."
            )

    with top_right:
        st.markdown('<div class="section-title">Distribución global</div>', unsafe_allow_html=True)
        fig = px.pie(
            values=[totals["used_gb"], totals["free_gb"]],
            names=["Usado", "Libre"],
            hole=0.68,
            color_discrete_sequence=["#60a5fa", "#1e3a8a"],
        )
        fig.update_traces(
            textinfo="percent",
            hovertemplate="%{label}: %{value:.1f} GB (%{percent})<extra></extra>"
        )
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#eef2f7"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Estado visual de nodos</div>', unsafe_allow_html=True)

    cols_per_row = 4
    rows = [EXPECTED_NODES[i:i + cols_per_row] for i in range(0, len(EXPECTED_NODES), cols_per_row)]

    for row_nodes in rows:
        cols = st.columns(cols_per_row)
        for idx, node_id in enumerate(row_nodes):
            node = nodes.get(node_id, {})
            report = reports_cache.get(node_id)

            status = safe_text(node.get("status"), "SIN DATOS")
            last_seen = safe_text(node.get("last_seen"))

            total_gb = used_gb = free_gb = util_pct = 0.0
            if report:
                raw = report.get("raw_payload") or {}
                disks = normalize_disks_from_payload(raw)
                total_gb, used_gb, free_gb, util_pct = sum_disk_usage_gb(disks)

            color = get_usage_color(util_pct)

            status_html = (
                '<span class="badge badge-ok">UP</span>'
                if status == "UP"
                else '<span class="badge badge-down">No reporta</span>'
            )

            with cols[idx]:
                st.markdown(
                    f"""
                    <div class="node-card">
                        <div class="node-name">{node_id}</div>
                        <div class="node-status">{status_html}</div>
                        <div class="node-meta"><b>Total:</b> {total_gb:.1f} GB</div>
                        <div class="node-meta"><b>Usado:</b> {used_gb:.1f} GB</div>
                        <div class="node-meta"><b>Libre:</b> {free_gb:.1f} GB</div>
                        <div class="node-meta"><b>Utilización:</b> {util_pct:.1f}%</div>
                        <div class="progress-wrap">
                            <div class="progress-fill" style="width:{util_pct}%; background:{color};"></div>
                        </div>
                        <div class="small-note">Último reporte: {last_seen}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# =========================================================
# TAB 2: NODOS
# =========================================================
with tab_nodos:
    st.markdown('<div class="section-title">Estado detallado de nodos</div>', unsafe_allow_html=True)

    filter_cols = st.columns(3)
    with filter_cols[0]:
        estado_filter = st.selectbox(
            "Filtrar por estado",
            ["TODOS", "UP", "NO_REPORTA", "SIN DATOS"],
            index=0,
        )
    with filter_cols[1]:
        text_filter = st.text_input("Buscar nodo", placeholder="Ej: LPZ-01")
    with filter_cols[2]:
        sort_by = st.selectbox(
            "Ordenar por",
            ["Nodo", "% Uso", "Total (GB)", "Usado (GB)", "Libre (GB)"],
            index=0,
        )

    table_rows = []
    for node_id in EXPECTED_NODES:
        node = nodes.get(node_id, {})
        report = reports_cache.get(node_id)

        status = safe_text(node.get("status"), "SIN DATOS")
        last_seen = safe_text(node.get("last_seen"))

        disk_summary = "—"
        util_pct_value = None
        total_gb = 0.0
        used_gb = 0.0
        free_gb = 0.0

        if report:
            raw = report.get("raw_payload") or {}
            disks = normalize_disks_from_payload(raw)
            total_gb, used_gb, free_gb, pct = sum_disk_usage_gb(disks)
            util_pct_value = pct
            disk_summary = f"{used_gb:.1f} / {total_gb:.1f} GB" if total_gb > 0 else "—"

        row = {
            "Estado": format_status(status),
            "Estado raw": status,
            "Nodo": node_id,
            "Último reporte (UTC)": last_seen,
            "Uso disco": disk_summary,
            "% Uso": round(util_pct_value, 2) if util_pct_value is not None else None,
            "Total (GB)": round(total_gb, 2),
            "Usado (GB)": round(used_gb, 2),
            "Libre (GB)": round(free_gb, 2),
        }
        table_rows.append(row)

    df_nodes = pd.DataFrame(table_rows)

    if estado_filter != "TODOS":
        df_nodes = df_nodes[df_nodes["Estado raw"] == estado_filter]

    if text_filter.strip():
        df_nodes = df_nodes[df_nodes["Nodo"].str.contains(text_filter.strip(), case=False, na=False)]

    ascending = True
    if sort_by in ["% Uso", "Total (GB)", "Usado (GB)", "Libre (GB)"]:
        ascending = False

    df_nodes = df_nodes.sort_values(by=sort_by, ascending=ascending, na_position="last").reset_index(drop=True)

    st.dataframe(
        df_nodes.drop(columns=["Estado raw"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown('<div class="section-title">Detalle de nodo</div>', unsafe_allow_html=True)

    selected_node = st.selectbox("Seleccionar nodo", EXPECTED_NODES, key="selected_node")
    report = reports_cache.get(selected_node)
    node = nodes.get(selected_node, {})

    info1, info2, info3 = st.columns(3)
    info1.metric("Nodo", selected_node)
    info2.metric("Estado", safe_text(node.get("status"), "SIN DATOS"))
    info3.metric("Último reporte", safe_text(node.get("last_seen")))

    if not report:
        st.warning(f"⏳ Sin datos disponibles para **{selected_node}**.")
    else:
        raw = report.get("raw_payload") or {}
        disks = normalize_disks_from_payload(raw)
        extra = raw.get("extra") or {}

        col_ts, col_extra = st.columns(2)

        with col_ts:
            st.markdown("**⏱️ Timestamps del reporte**")
            st.text(f"Reportado por cliente : {safe_text(report.get('client_reported_at'))}")
            st.text(f"Recibido por servidor : {safe_text(report.get('server_received_at'))}")
            st.text(f"Intervalo configurado : {safe_text(report.get('interval_seconds'))}s")

        with col_extra:
            st.markdown("**🌐 Datos extra del nodo**")
            ip = extra.get("ip") or raw.get("ip")
            mac = extra.get("mac") or raw.get("mac")
            ram_total = extra.get("ram_total_bytes") or raw.get("ram_total_bytes")
            ram_used = extra.get("ram_used_bytes") or raw.get("ram_used_bytes")

            st.text(f"IP  : {safe_text(ip, 'No disponible')}")
            st.text(f"MAC : {safe_text(mac, 'No disponible')}")

            ram_total_gb = bytes_to_gb(ram_total or 0)
            ram_used_gb = bytes_to_gb(ram_used or 0)
            if ram_total_gb > 0:
                st.text(f"RAM : {ram_used_gb:.1f} / {ram_total_gb:.1f} GB")
            else:
                st.text("RAM : No disponible")

        st.markdown(f"**💾 Discos detectados en {selected_node}**")

        if not disks:
            st.info("Sin datos de discos.")
        else:
            disk_rows = []
            for d in disks:
                total = bytes_to_gb(d.get("total_bytes", 0))
                used = bytes_to_gb(d.get("used_bytes", 0))
                free = bytes_to_gb(d.get("free_bytes", 0))
                pct = (used / total * 100) if total > 0 else 0.0
                iops = d.get("iops")

                disk_rows.append({
                    "Dispositivo": d.get("disk_name", "—"),
                    "Tipo": d.get("disk_type", "—"),
                    "Total (GB)": round(total, 2),
                    "Usado (GB)": round(used, 2),
                    "Libre (GB)": round(free, 2),
                    "% Uso": round(pct, 2),
                    "IOPS": f"{int(iops):,}" if iops not in (None, "") else "—",
                })

            st.dataframe(pd.DataFrame(disk_rows), use_container_width=True, hide_index=True)

# =========================================================
# TAB 3: HISTÓRICO
# =========================================================
with tab_hist:
    st.markdown('<div class="section-title">Histórico y estadísticas por nodo</div>', unsafe_allow_html=True)

    history_cols = st.columns(3)
    with history_cols[0]:
        hist_node = st.selectbox("Nodo para análisis histórico", EXPECTED_NODES, key="hist_node")
    with history_cols[1]:
        start_date = st.date_input(
            "Fecha inicio",
            value=date.today() - timedelta(days=7),
            key="hist_start",
        )
    with history_cols[2]:
        end_date = st.date_input(
            "Fecha fin",
            value=date.today(),
            key="hist_end",
        )

    if start_date > end_date:
        st.error("La fecha de inicio no puede ser mayor que la fecha fin.")
        st.stop()

    history_data = None
    history_error = None

    try:
        history_data = load_history(hist_node, start_date=start_date, end_date=end_date)
    except Exception as e:
        history_error = str(e)

    if history_error:
        st.error(f"Error cargando historial: {history_error}")
    elif history_data is None:
        st.warning("Falta `get_reports_history(node_id, start_date=None, end_date=None)` en `data.py`.")
    else:
        hist_df = build_history_dataframe(history_data, hist_node)

        if hist_df.empty:
            st.info("No hay datos históricos en el rango seleccionado.")
        else:
            s1, s2, s3, s4, s5 = st.columns(5)

            avg_used = hist_df["Usado (GB)"].mean()
            max_used = hist_df["Usado (GB)"].max()
            min_used = hist_df["Usado (GB)"].min()
            avg_util = hist_df["% Uso"].mean()

            growth = 0.0
            if len(hist_df) >= 2:
                growth = hist_df["Usado (GB)"].iloc[-1] - hist_df["Usado (GB)"].iloc[0]

            s1.metric("Promedio uso", f"{avg_used:.2f} GB")
            s2.metric("Máximo uso", f"{max_used:.2f} GB")
            s3.metric("Mínimo uso", f"{min_used:.2f} GB")
            s4.metric("Promedio % uso", f"{avg_util:.2f}%")
            s5.metric("Crecimiento", f"{growth:.2f} GB")

            st.markdown("### 📋 Tabla histórica")
            st.dataframe(hist_df, use_container_width=True, hide_index=True)

            st.markdown("### 📊 Evolución del uso")
            chart_metric = st.selectbox(
                "Métrica a graficar",
                ["Usado (GB)", "Libre (GB)", "Total (GB)", "% Uso"],
                index=0,
                key="hist_metric",
            )

            line_chart = (
                alt.Chart(hist_df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("Fecha:T", title="Fecha"),
                    y=alt.Y(f"{chart_metric}:Q", title=chart_metric),
                    tooltip=["Fecha:T", "Usado (GB):Q", "Libre (GB):Q", "Total (GB):Q", "% Uso:Q"],
                )
                .properties(height=380)
            )
            st.altair_chart(line_chart, use_container_width=True)

            if len(hist_df) >= 2:
                st.markdown("### 📌 Variación entre el primer y último registro")

                first_row = hist_df.iloc[0]
                last_row = hist_df.iloc[-1]

                v1, v2, v3, v4 = st.columns(4)
                v1.metric(
                    "Usado",
                    f"{last_row['Usado (GB)']:.2f} GB",
                    delta=f"{(last_row['Usado (GB)'] - first_row['Usado (GB)']):.2f} GB",
                )
                v2.metric(
                    "Libre",
                    f"{last_row['Libre (GB)']:.2f} GB",
                    delta=f"{(last_row['Libre (GB)'] - first_row['Libre (GB)']):.2f} GB",
                )
                v3.metric(
                    "Total",
                    f"{last_row['Total (GB)']:.2f} GB",
                    delta=f"{(last_row['Total (GB)'] - first_row['Total (GB)']):.2f} GB",
                )
                v4.metric(
                    "% Uso",
                    f"{last_row['% Uso']:.2f}%",
                    delta=f"{(last_row['% Uso'] - first_row['% Uso']):.2f}%",
                )

# =========================================================
# TAB 4: COMANDOS
# =========================================================
with tab_cmd:
    st.markdown('<div class="section-title">Enviar comando a nodo</div>', unsafe_allow_html=True)

    cmd_col1, cmd_col2 = st.columns([1, 2])
    with cmd_col1:
        cmd_node = st.selectbox("Nodo destino", EXPECTED_NODES, key="cmd_node")
    with cmd_col2:
        cmd_text = st.text_input("Comando", placeholder="Ej: ping, reiniciar_servicio")

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