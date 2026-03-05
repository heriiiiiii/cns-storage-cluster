"""
test_server.py
--------------
Servidor TCP de prueba LOCAL para verificar que el cliente envia datos correctos.
Recibe reportes del cliente y los guarda directo en Supabase.

USAR SOLO PARA TESTING - no es el servidor final de tus companeros.

Requiere: pip install supabase
"""
import json
import socket
import threading
from datetime import datetime, timezone
from uuid import uuid4

# ---- Supabase ----
try:
    from supabase import create_client, Client
    SUPABASE_URL = "https://csmgwdlixlxjchgmrttx.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzbWd3ZGxpeGx4amNoZ21ydHR4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjU0NTI1NiwiZXhwIjoyMDg4MTIxMjU2fQ.45LcdF7qT0mulDf-Uz2uk7fMqx-ztf9CMPDgNkitTg0"
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("[OK] Conectado a Supabase")
except ImportError:
    supabase = None
    print("[AVISO] supabase-py no instalado. Ejecuta: pip install supabase")
    print("[INFO] El servidor igual funcionara pero no guardara en BD.")

HOST = "localhost"
PORT = 5000
NEWLINE = chr(10)


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def save_to_supabase(payload: dict):
    """
    Persiste el reporte en Supabase siguiendo el esquema de tus companeros:
      1. Upsert en nodes
      2. Insert en reports
      3. Insert en disk_metrics (una fila por disco)
    """
    if not supabase:
        print("  [BD] Supabase no disponible, solo mostrando datos.")
        return

    node_code = payload.get("node_code", "UNKNOWN")
    server_received_at = now_utc()

    try:
        # 1. Buscar el nodo - imprimir TODO para diagnostico
        all_nodes = supabase.table("nodes").select("id, node_id, node_name").execute()
        print(f"  [BD DIAGNOSTICO] Todos los nodos en BD: {all_nodes.data}")

        existing = supabase.table("nodes").select("id").eq("node_id", node_code).execute()
        print(f"  [BD DIAGNOSTICO] Busqueda de {repr(node_code)}: {existing.data}")

        if not existing.data:
            # Intentar con node_name por si acaso
            existing = supabase.table("nodes").select("id").eq("node_name", node_code).execute()
            print(f"  [BD DIAGNOSTICO] Busqueda por node_name: {existing.data}")

        if existing.data:
            node_uuid = existing.data[0]["id"]
            supabase.table("nodes").update(
                {"status": "ACTIVE", "last_seen": server_received_at}
            ).eq("id", node_uuid).execute()
            print(f"  [BD] Nodo encontrado y actualizado. UUID: {node_uuid}")
        else:
            insert_resp = supabase.table("nodes").insert(
                {
                    "node_id": node_code,
                    "node_name": node_code,
                    "status": "ACTIVE",
                    "last_seen": server_received_at,
                }
            ).execute()
            print(f"  [BD] Nodo insertado: {insert_resp.data}")
            node_uuid = insert_resp.data[0]["id"]

        # 2. Insert en reports
        report_resp = supabase.table("reports").insert(
            {
                "node_id": node_code,
                "client_reported_at": payload.get("client_reported_at"),
                "server_received_at": server_received_at,
                "interval_seconds": payload.get("interval_seconds", 10),
                "raw_payload": payload,
            }
        ).execute()

        report_uuid = report_resp.data[0]["id"]

        # 3. Insert en disk_metrics (una fila por disco)
        disks = payload.get("disks", [])
        for disk in disks:
            supabase.table("disk_metrics").insert(
                {
                    "report_id": report_uuid,
                    "disk_name": disk.get("disk_name"),
                    "disk_type": disk.get("disk_type"),
                    "total_bytes": disk.get("total_bytes"),
                    "used_bytes": disk.get("used_bytes"),
                    "free_bytes": disk.get("free_bytes"),
                    "iops": disk.get("iops"),
                }
            ).execute()

        print(f"  [BD] Guardado en Supabase -> node: {node_code} | report_id: {report_uuid}")

    except Exception as e:
        print(f"  [BD ERROR] {e}")


def handle_client(conn: socket.socket, addr):
    """Maneja un cliente conectado: recibe reportes y envia ACK."""
    print(f"[+] Cliente conectado: {addr}")
    buffer = ""

    try:
        while True:
            chunk = conn.recv(4096).decode("utf-8")
            if not chunk:
                break
            buffer += chunk

            while NEWLINE in buffer:
                line, buffer = buffer.split(NEWLINE, 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    payload = json.loads(line)
                    msg_type = payload.get("type", "")
                    node = payload.get("node_code", "?")

                    if msg_type == "REPORT":
                        print(f"\n[REPORTE] Nodo: {node} | Disco: {payload['disks'][0]['disk_name']}")
                        print(f"  total_bytes : {payload['disks'][0].get('total_bytes')}")
                        print(f"  used_bytes  : {payload['disks'][0].get('used_bytes')}")
                        print(f"  free_bytes  : {payload['disks'][0].get('free_bytes')}")
                        print(f"  iops        : {payload['disks'][0].get('iops')}")
                        print(f"  extra.ip    : {payload.get('extra', {}).get('ip')}")
                        print(f"  extra.mac   : {payload.get('extra', {}).get('mac')}")
                        save_to_supabase(payload)

                    elif msg_type == "ACK":
                        print(f"[ACK] Nodo {node} confirmo mensaje: {payload.get('message_id')}")

                    else:
                        print(f"[?] Tipo desconocido de {node}: {msg_type}")

                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON invalido: {e} | raw: {line[:80]}")

    except Exception as e:
        print(f"[-] Cliente {addr} desconectado: {e}")
    finally:
        conn.close()
        print(f"[-] Conexion cerrada: {addr}")


def run_test_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(9)

    print("=" * 55)
    print("  SERVIDOR DE PRUEBA CNS")
    print("=" * 55)
    print(f"  Escuchando en {HOST}:{PORT}")
    print(f"  Supabase: {'Conectado' if supabase else 'No disponible'}")
    print("  Ctrl+C para detener")
    print("=" * 55)
    print()

    try:
        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[INFO] Servidor detenido.")
    finally:
        server_sock.close()


if __name__ == "__main__":
    run_test_server()
