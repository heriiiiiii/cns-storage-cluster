import socket
import json
import uuid
import threading
import logging
from datetime import datetime

from config import HOST, PORT, ADMIN_PORT
from cluster_state import ClusterState
from client_handler import ClientHandler
from monitor import MonitorThread

try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("[ADMIN] Flask no disponible. Instala: pip install flask")


def send_command(cluster_state: ClusterState, node_id: str, command: str, payload: dict | None = None):
    conn = cluster_state.get_conn(node_id)
    if conn is None:
        print(f"[!] No hay conexión activa para {node_id}")
        return

    msg_id = str(uuid.uuid4())

    # Formato que el cliente entiende
    msg = {
        "type": "server_message",
        "message_id": msg_id,
        "content": command,
        "payload": payload or {},
        "server_timestamp": datetime.utcnow().isoformat() + "Z",
    }

    wire = json.dumps(msg) + "\n"

    try:
        conn.sendall(wire.encode("utf-8"))
        cluster_state.track_message_sent(msg_id, node_id)
        print(f"[→] Enviado server_message a {node_id}: {command} (message_id={msg_id})")
    except Exception as e:
        print(f"[!] Error enviando a {node_id}: {e}")


def _extract_disk_gb_safe(cluster_state: ClusterState, metrics: dict):
    """
    Usa el extractor del ClusterState si existe; si no, fallback simple.
    Retorna (total_gb, used_gb, free_gb).
    """
    if hasattr(cluster_state, "_extract_disk_gb"):
        return cluster_state._extract_disk_gb(metrics)  # type: ignore

    # fallback mínimo
    disk = metrics.get("disk") or {}
    if "total_gb" in disk:
        t = float(disk.get("total_gb") or 0)
        u = float(disk.get("used_gb") or 0)
        f = float(disk.get("free_gb") or 0)
        return t, u, f

    disks = metrics.get("disks") or []
    if disks and isinstance(disks[0], dict):
        d0 = disks[0]
        BYTES_TO_GB = 1024**3
        t = float(d0.get("total_bytes") or 0) / BYTES_TO_GB
        u = float(d0.get("used_bytes") or 0) / BYTES_TO_GB
        f = float(d0.get("free_bytes") or 0) / BYTES_TO_GB
        return t, u, f

    return 0.0, 0.0, 0.0


def console_thread(cluster_state: ClusterState):
    """
    Consola interactiva del servidor.

    Comandos:
      - status
      - cmd <NODE_ID> <COMMAND...>
      - cmdall <COMMAND...>
    """
    # Solo para “orden” visual, pero no bloquea nodos extra
    order_preferido = ["ORU-01", "LPZ-01", "SCZ-01", "BEN-01", "TJA-01", "PND-01", "CBBA-01", "CHQ-01", "PTS-01"]

    while True:
        try:
            line = input().strip()
            if not line:
                continue

            # ====== STATUS ======
            if line.lower() == "status":
                snap = cluster_state.get_snapshot()
                totals = cluster_state.compute_totals()

                print("\n========== MONITOR NACIONAL DE ALMACENAMIENTO ==========")
                print(f"Reportan: {totals['reporting']} de {len(snap)} conectados (o conocidos)")
                print(
                    f"Total: {totals['total_gb']:.1f} GB | "
                    f"Usado: {totals['used_gb']:.1f} GB | "
                    f"Libre: {totals['free_gb']:.1f} GB"
                )
                print(f"Utilización global: {totals['util_percent']:.1f}%")
                print("-------------------------------------------------------")
                print("Nodo      Estado   Último reporte (UTC)                 %Uso   Usado/Total")
                print("-------------------------------------------------------")

                # imprimimos primero los “esperados” cortos
                for node_id in order_preferido:
                    data = snap.get(node_id)
                    if not data:
                        print(f"{node_id:<8} {'NO REG':<7} {'-':<30} {'-':<5} {'-'}")
                        continue

                    status = data.get("status", "DOWN")
                    last_seen = data.get("last_seen")
                    last_seen_str = str(last_seen) if last_seen else "-"
                    m = data.get("metrics")

                    if status != "UP" or not m:
                        label = "UP" if status == "UP" else "NO REP"
                        print(f"{node_id:<8} {label:<7} {last_seen_str:<30} {'-':<5} {'-'}")
                        continue

                    t, u, _f = _extract_disk_gb_safe(cluster_state, m)
                    pct = (u / t * 100.0) if t > 0 else 0.0
                    print(f"{node_id:<8} {'UP':<7} {last_seen_str:<30} {pct:>4.0f}%  {u:.1f}/{t:.1f} GB")

                # nodos extra conectados (como LPZ-01)
                extras = [nid for nid in snap.keys() if nid not in set(order_preferido)]
                if extras:
                    print("-------------------------------------------------------")
                    for nid in sorted(extras):
                        data = snap.get(nid, {})
                        status = data.get("status", "DOWN")
                        last_seen = data.get("last_seen")
                        last_seen_str = str(last_seen) if last_seen else "-"
                        m = data.get("metrics")

                        if status != "UP" or not m:
                            label = "UP" if status == "UP" else "NO REP"
                            print(f"{nid:<8} {label:<7} {last_seen_str:<30} {'-':<5} {'-'}")
                            continue

                        t, u, _f = _extract_disk_gb_safe(cluster_state, m)
                        pct = (u / t * 100.0) if t > 0 else 0.0
                        print(f"{nid:<8} {'UP':<7} {last_seen_str:<30} {pct:>4.0f}%  {u:.1f}/{t:.1f} GB")

                print("=======================================================\n")
                continue

            # Parse general
            parts = line.split()
            cmd = parts[0].lower()

            # ====== CMD a un nodo (acepta NODE_ID con guiones y comando con espacios) ======
            if cmd == "cmd" and len(parts) >= 3:
                node_id = parts[1]  # NO upper() para respetar LPZ-01
                command = " ".join(parts[2:])  # permite espacios

                snap = cluster_state.get_snapshot()
                if node_id not in snap:
                    print(f"[!] NODE_ID no conectado/registrado: {node_id}. Conectados: {sorted(snap.keys())}")
                    continue

                send_command(cluster_state, node_id, command, payload={})
                continue

            # ====== CMDALL a todos los nodos UP conectados ======
            if cmd == "cmdall" and len(parts) >= 2:
                command = " ".join(parts[1:])
                snap = cluster_state.get_snapshot()

                sent = 0
                for node_id, data in snap.items():
                    if data.get("status") != "UP":
                        continue
                    if cluster_state.get_conn(node_id) is None:
                        continue
                    send_command(cluster_state, node_id, command, payload={})
                    sent += 1

                print(f"[→] Enviados {sent} comandos '{command}' a nodos UP.")
                continue

            print("Comandos: status | cmd <NODE_ID> <COMMAND...> | cmdall <COMMAND...>")

        except Exception as e:
            print("[!] consola:", e)


def start_admin_api(cluster_state: ClusterState):
    """API HTTP minima para que el dashboard pueda enviar comandos."""
    if not FLASK_AVAILABLE:
        return

    app = Flask("cns-admin")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    @app.route("/command", methods=["POST"])
    def post_command():
        data = request.get_json(silent=True) or {}
        node_id = data.get("node_id")
        command = data.get("command")
        if not node_id or not command:
            return jsonify({"error": "node_id y command son requeridos"}), 400
        send_command(cluster_state, node_id, command)
        return jsonify({"ok": True, "node_id": node_id, "command": command})

    @app.route("/nodes", methods=["GET"])
    def get_nodes():
        snap = cluster_state.get_snapshot()
        result = {}
        for nid, data in snap.items():
            last_seen = data.get("last_seen")
            result[nid] = {
                "status":    data.get("status"),
                "last_seen": str(last_seen) if last_seen else None,
                "region":    data.get("region"),
            }
        return jsonify(result)

    print(f"[ADMIN] API HTTP escuchando en 0.0.0.0:{ADMIN_PORT}")
    app.run(host="0.0.0.0", port=ADMIN_PORT, debug=False, use_reloader=False)


def start_server():
    cluster_state = ClusterState()

    monitor = MonitorThread(cluster_state)
    monitor.start()

    threading.Thread(target=console_thread, args=(cluster_state,), daemon=True).start()
    threading.Thread(target=start_admin_api, args=(cluster_state,), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"🚀 Servidor escuchando en {HOST}:{PORT}")
        print("Escribe: status | cmd <NODE_ID> <COMMAND...> | cmdall <COMMAND...>")

        while True:
            conn, addr = server.accept()
            handler = ClientHandler(conn, addr, cluster_state)
            handler.start()


if __name__ == "__main__":
    start_server()