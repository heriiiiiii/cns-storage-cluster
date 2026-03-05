#este arrancara el servidor

import socket
import json
import uuid
import threading
from datetime import datetime

from config import HOST, PORT, EXPECTED_NODES
from cluster_state import ClusterState
from client_handler import ClientHandler
from monitor import MonitorThread

def send_command(cluster_state: ClusterState, node_id: str, command: str, payload: dict | None = None):
    conn = cluster_state.get_conn(node_id)
    if conn is None:
        print(f"[!] No hay conexión activa para {node_id}")
        return

    msg_id = str(uuid.uuid4())
    msg = {
        "type": "command",
        "msg_id": msg_id,
        "command": command,
        "payload": payload or {},
        "server_timestamp": datetime.utcnow().isoformat() + "Z"
    }
    wire = json.dumps(msg) + "\n"

    try:
        conn.sendall(wire.encode())
        cluster_state.track_message_sent(msg_id, node_id)
        print(f"[→] Enviado command a {node_id}: {command} (msg_id={msg_id})")
    except Exception as e:
        print(f"[!] Error enviando a {node_id}: {e}")

def console_thread(cluster_state: ClusterState):
    """
    Consola interactiva del servidor.

    Comandos:
      - status
      - cmd <NODE_ID> <COMMAND>
      - cmdall <COMMAND>
    """
    order = ["ORU","LPZ","SCZ","BEN","TJA","PND","CBBA","CHQ","PTS"]

    while True:
        try:
            line = input().strip()
            if not line:
                continue

            # ====== STATUS (dashboard en consola) ======
            if line.lower() == "status":
                snap = cluster_state.get_snapshot()
                totals = cluster_state.compute_totals()

                print("\n========== MONITOR NACIONAL DE ALMACENAMIENTO ==========")
                print(f"Reportan: {totals['reporting']} de 9")
                print(
                    f"Total: {totals['total_gb']:.1f} GB | "
                    f"Usado: {totals['used_gb']:.1f} GB | "
                    f"Libre: {totals['free_gb']:.1f} GB"
                )
                print(f"Utilización global: {totals['util_percent']:.1f}%")
                print("-------------------------------------------------------")
                print("Nodo   Estado   Último reporte (UTC)                %Uso   Usado/Total")
                print("-------------------------------------------------------")

                for node_id in order:
                    data = snap.get(node_id)

                    # Nunca se conectó (ni hello)
                    if not data:
                        print(f"{node_id:<5} {'NO REG':<7} {'-':<30} {'-':<5} {'-'}")
                        continue

                    status = data.get("status", "DOWN")
                    last_seen = data.get("last_seen")
                    last_seen_str = str(last_seen) if last_seen else "-"

                    m = data.get("metrics")

                    # Conocido pero no reporta (timeout o sin metrics)
                    if status != "UP" or not m:
                        # si está registrado pero no reporta, lo marcamos así
                        label = "UP" if status == "UP" else "NO REP"
                        print(f"{node_id:<5} {label:<7} {last_seen_str:<30} {'-':<5} {'-'}")
                        continue

                    disk = (m.get("disk") or {})
                    t = float(disk.get("total_gb") or 0)
                    u = float(disk.get("used_gb") or 0)
                    pct = (u / t * 100.0) if t > 0 else 0.0

                    print(f"{node_id:<5} {'UP':<7} {last_seen_str:<30} {pct:>4.0f}%   {u:.0f}/{t:.0f} GB")

                # Si hay nodos extra conectados (no esperados) los listamos abajo
                extras = [nid for nid in snap.keys() if nid not in set(order)]
                if extras:
                    print("-------------------------------------------------------")
                    print("Nodos extra detectados:", ", ".join(extras))

                print("=======================================================\n")
                continue

            # ====== CMD a un nodo ======
            parts = line.split()
            if parts[0] == "cmd" and len(parts) >= 3:
                node_id = parts[1].upper()
                command = parts[2]

                if node_id not in EXPECTED_NODES:
                    print(f"[!] NODE_ID inválido: {node_id}. Esperados: {sorted(EXPECTED_NODES)}")
                    continue

                send_command(cluster_state, node_id, command, payload={})
                continue

            # ====== CMD a todos los nodos UP ======
            if parts[0] == "cmdall" and len(parts) >= 2:
                command = parts[1]
                snap = cluster_state.get_snapshot()

                sent = 0
                for node_id in EXPECTED_NODES:
                    data = snap.get(node_id)
                    if not data:
                        continue
                    if data.get("status") != "UP":
                        continue
                    # intenta mandar solo si tiene conexión viva
                    if cluster_state.get_conn(node_id) is None:
                        continue
                    send_command(cluster_state, node_id, command, payload={})
                    sent += 1

                print(f"[→] Enviados {sent} comandos '{command}' a nodos UP.")
                continue

            print("Comandos: status | cmd <NODE_ID> <COMMAND> | cmdall <COMMAND>")

        except Exception as e:
            print("[!] consola:", e)

def start_server():
    cluster_state = ClusterState()

    monitor = MonitorThread(cluster_state)
    monitor.start()

    threading.Thread(target=console_thread, args=(cluster_state,), daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"🚀 Servidor escuchando en {HOST}:{PORT}")
        print("Escribe: status | cmd <NODE_ID> <COMMAND>")

        while True:
            conn, addr = server.accept()
            handler = ClientHandler(conn, addr, cluster_state)
            handler.start()

if __name__ == "__main__":
    start_server()