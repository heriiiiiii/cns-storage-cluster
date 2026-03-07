# client_handler.py

import threading
from datetime import datetime

from protocol import parse_message
from config import EXPECTED_NODES, ENFORCE_EXPECTED_NODES

# DB (Supabase) - si falla, el server sigue funcionando
DB_AVAILABLE = True
try:
    from db import insert_report, upsert_node, insert_disk_metrics
except Exception as e:
    DB_AVAILABLE = False
    print(f"[DB] db.py no disponible o error al importar: {e}")


class ClientHandler(threading.Thread):

    def __init__(self, conn, addr, cluster_state):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.cluster_state = cluster_state
        self.node_id = None

    def run(self):

        print(f"[+] Nueva conexión desde {self.addr}")

        buffer = ""

        while True:

            try:

                data = self.conn.recv(4096)

                if not data:
                    break

                buffer += data.decode(errors="replace")

                while "\n" in buffer:

                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue

                    message = parse_message(line)

                    if message is None:
                        print(f"[!] JSON inválido desde {self.addr}: {line[:120]}")
                        continue

                    self.handle_message(message)

            except Exception as e:

                print(f"[!] Error con {self.addr}: {e}")
                break

        try:
            self.conn.close()
        except Exception:
            pass

        print(f"[-] Conexión cerrada {self.addr} (node_id={self.node_id})")

    # -------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------
    def _validate_node(self, node_id: str):

        if not node_id:
            return False

        if ENFORCE_EXPECTED_NODES and EXPECTED_NODES:
            return node_id in EXPECTED_NODES

        return True

    # -------------------------------------------------------------
    # Normalizar timestamp cliente
    # -------------------------------------------------------------
    def _normalize_timestamp(self, payload: dict):

        ts = (
            payload.get("timestamp")
            or payload.get("client_timestamp")
            or payload.get("client_reported_at")
        )

        if not ts:
            return None

        try:
            return datetime.fromisoformat(ts.replace("Z", ""))
        except Exception:
            return None

    # -------------------------------------------------------------
    # Guardar reporte en DB
    # -------------------------------------------------------------
    def _db_save_report_and_node(self, node_id: str, payload: dict):

        if not DB_AVAILABLE:
            return

        server_received_at = datetime.utcnow().isoformat() + "Z"

        client_reported_at = payload.get("client_reported_at") or payload.get("client_timestamp")

        interval_seconds = payload.get("interval_seconds")

        report_id = None

        try:

            resp = insert_report(
                node_id=node_id,
                client_reported_at=client_reported_at,
                server_received_at=server_received_at,
                interval_seconds=interval_seconds,
                raw_payload=payload,
            )

            if resp and resp.data:
                report_id = resp.data[0]["id"]

        except Exception as e:

            print(f"[DB] Error insert_report({node_id}): {e}")

        if report_id:

            try:
                insert_disk_metrics(report_id, payload.get("disks", []))
            except Exception as e:
                print(f"[DB] Error insert_disk_metrics({node_id}): {e}")

        node_name = payload.get("node_name") or payload.get("region")

        try:

            upsert_node(
                node_id=node_id,
                status="UP",
                last_seen=server_received_at,
                addr=str(self.addr),
                node_name=node_name,
            )

        except Exception as e:

            print(f"[DB] Error upsert_node({node_id}): {e}")

    # -------------------------------------------------------------
    # Message handling
    # -------------------------------------------------------------
    def handle_message(self, message: dict):

        msg_type = (message.get("type") or "").strip()
        msg_type_norm = msg_type.lower()

        # =========================================================
        # REPORT (nuevo cliente)
        # =========================================================
        if msg_type_norm == "report":

            node_code = message.get("node_code") or message.get("node_id")

            if not self._validate_node(node_code):
                print(f"[!] Nodo no permitido: {node_code} desde {self.addr}")
                return

            # registrar conexión si aún no hubo hello
            if not self.node_id:

                self.node_id = node_code

                self.cluster_state.register_or_update_connection(
                    node_id=self.node_id,
                    region=message.get("region"),
                    conn=self.conn,
                    addr=self.addr,
                )

                print(f"[✓] Nodo auto-registrado por REPORT: {self.node_id}")

            # normalizar timestamp cliente
            client_time = self._normalize_timestamp(message)

            if client_time:
                message["timestamp"] = client_time.isoformat()

            # guardar métricas en memoria
            self.cluster_state.update_metrics(self.node_id, message)

            print(f"[📊] REPORT recibido de {self.node_id}")

            # guardar en BD
            self._db_save_report_and_node(self.node_id, message)

            return

        # =========================================================
        # HELLO
        # =========================================================
        if msg_type_norm == "hello":

            node_id = message.get("node_id") or message.get("node_code")

            if not self._validate_node(node_id):
                print(f"[!] Nodo no permitido o sin node_id: {node_id} desde {self.addr}")
                return

            self.node_id = node_id

            region = message.get("region")

            self.cluster_state.register_or_update_connection(
                node_id=node_id,
                region=region,
                conn=self.conn,
                addr=self.addr
            )

            print(f"[✓] Nodo registrado/actualizado: {node_id} ({region})")

            if DB_AVAILABLE:

                try:

                    upsert_node(
                        node_id=node_id,
                        status="UP",
                        last_seen=datetime.utcnow().isoformat() + "Z",
                        addr=str(self.addr),
                        node_name=region,
                    )

                except Exception as e:

                    print(f"[DB] Error upsert_node(hello) {node_id}: {e}")

            return

        # =========================================================
        # METRICS
        # =========================================================
        if msg_type_norm == "metrics":

            if not self.node_id:
                print("[!] Metrics recibidas sin HELLO")
                return

            self.cluster_state.update_metrics(self.node_id, message)

            print(f"[📊] Metrics actualizadas de {self.node_id}")

            self._db_save_report_and_node(self.node_id, message)

            return

        # =========================================================
        # ACK
        # =========================================================
        if msg_type_norm in ("ack", "acknowledge"):

            msg_id = message.get("msg_id") or message.get("message_id")

            if not msg_id:
                print("[!] ACK sin msg_id")
                return

            ok = self.cluster_state.track_ack(msg_id)

            if ok:
                print(f"[ACK] {self.node_id} confirmó msg_id={msg_id}")
            else:
                print(f"[ACK?] msg_id desconocido: {msg_id}")

            return

        if msg_type == "ACK":

            msg_id = message.get("message_id") or message.get("msg_id")

            if not msg_id:
                print("[!] ACK sin message_id")
                return

            ok = self.cluster_state.track_ack(msg_id)

            if ok:
                print(f"[ACK] {self.node_id} confirmó msg_id={msg_id}")
            else:
                print(f"[ACK?] msg_id desconocido: {msg_id}")

            return

        print(f"[!] Tipo de mensaje desconocido: {msg_type}")