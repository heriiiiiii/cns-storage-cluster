#en este archivo se manejara cada cliente que se conecta al servidor, se le asignara un hilo para manejar su conexion y se le asignara un nodo para almacenar sus archivos.

import threading
from protocol import parse_message
from config import EXPECTED_NODES

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

        # Si se corta, no borramos el nodo; el monitor lo marcará DOWN por timeout
        try:
            self.conn.close()
        except:
            pass

        print(f"[-] Conexión cerrada {self.addr} (node_id={self.node_id})")

    def handle_message(self, message: dict):
        msg_type = message.get("type")
        node_id = message.get("node_id")

        if msg_type == "hello":
            if not node_id or node_id not in EXPECTED_NODES:
                print(f"[!] Nodo no permitido o sin node_id: {node_id} desde {self.addr}")
                return

            self.node_id = node_id
            region = message.get("region")

            # registrar o actualizar conexión (reconexión)
            self.cluster_state.register_or_update_connection(
                node_id=node_id, region=region, conn=self.conn, addr=self.addr
            )

            print(f"[✓] Nodo registrado/actualizado: {node_id} ({region})")

        elif msg_type == "metrics":
            # Aceptamos métricas solo si ya hubo hello (para asegurar identidad)
            if not self.node_id:
                print("[!] Metrics recibidas sin HELLO (se ignora)")
                return

            self.cluster_state.update_metrics(self.node_id, message)
            print(f"[📊] Metrics actualizadas de {self.node_id}")

        elif msg_type == "ack":
            msg_id = message.get("msg_id")
            if not msg_id:
                print("[!] ACK sin msg_id")
                return
            ok = self.cluster_state.track_ack(msg_id)
            if ok:
                print(f"[ACK] {self.node_id} confirmó msg_id={msg_id}")
            else:
                print(f"[ACK?] msg_id desconocido: {msg_id}")

        else:
            print(f"[!] Tipo de mensaje desconocido: {msg_type}")