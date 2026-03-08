# cluster_state.py

import threading
import json
from datetime import datetime

BYTES_TO_GB = 1024**3


class ClusterState:

    def __init__(self):

        self.lock = threading.Lock()

        # node_id -> {region,status,last_seen,metrics,conn,addr,client_time}
        self.nodes = {}

        # msg_id -> {node_id,sent_at,ack_at,status}
        self.pending_msgs = {}

    # -------------------------------------------------------
    # Registrar o actualizar conexión de nodo
    # -------------------------------------------------------
    def register_or_update_connection(self, node_id, region=None, conn=None, addr=None):

        now = datetime.utcnow()

        with self.lock:

            if node_id not in self.nodes:

                self.nodes[node_id] = {
                    "region": region,
                    "status": "UP",
                    "last_seen": now,
                    "metrics": None,
                    "conn": conn,
                    "addr": addr,
                    "client_time": None
                }

            else:

                self.nodes[node_id]["conn"] = conn
                self.nodes[node_id]["addr"] = addr

                if region:
                    self.nodes[node_id]["region"] = region

                self.nodes[node_id]["status"] = "UP"
                self.nodes[node_id]["last_seen"] = now

    # -------------------------------------------------------
    # Actualizar métricas del nodo
    # -------------------------------------------------------
    def update_metrics(self, node_id, metrics):

        now = datetime.utcnow()

        with self.lock:

            if node_id not in self.nodes:

                self.nodes[node_id] = {
                    "region": None,
                    "status": "UP",
                    "last_seen": now,
                    "metrics": metrics,
                    "conn": None,
                    "addr": None,
                    "client_time": None
                }

            else:

                self.nodes[node_id]["metrics"] = metrics
                self.nodes[node_id]["last_seen"] = now
                self.nodes[node_id]["status"] = "UP"

            # guardar hora reportada por el cliente (Modificación 1)
            client_ts = metrics.get("timestamp")

            if client_ts:

                try:
                    self.nodes[node_id]["client_time"] = datetime.fromisoformat(client_ts)
                except Exception:
                    pass

    # -------------------------------------------------------
    # Marcar nodo como DOWN si timeout
    # -------------------------------------------------------
    def mark_down_if_timeout(self, node_id):

        with self.lock:

            if node_id in self.nodes:

                # usamos NO_REPORTA como pidió tu compañero
                self.nodes[node_id]["status"] = "NO_REPORTA"

    # -------------------------------------------------------
    # Snapshot seguro del estado
    # -------------------------------------------------------
    def get_snapshot(self):

        with self.lock:

            snap = {}

            for k, v in self.nodes.items():

                snap[k] = {
                    "region": v.get("region"),
                    "status": v.get("status"),
                    "last_seen": v.get("last_seen"),
                    "metrics": v.get("metrics"),
                    "addr": v.get("addr"),
                    "client_time": v.get("client_time")
                }

            return snap

    # -------------------------------------------------------
    # Obtener conexión de nodo
    # -------------------------------------------------------
    def get_conn(self, node_id):

        with self.lock:

            node = self.nodes.get(node_id)

            return None if not node else node.get("conn")

    # -------------------------------------------------------
    # Enviar actualización de configuración al nodo
    # -------------------------------------------------------
    def notify_config_update(self, node_id, message):

        conn = self.get_conn(node_id)

        if not conn:
            return False

        payload = {
            "type": "config_update",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:

            conn.sendall(json.dumps(payload).encode())

            return True

        except Exception:

            return False

    # -------------------------------------------------------
    # Tracking de mensajes enviados
    # -------------------------------------------------------
    def track_message_sent(self, msg_id, node_id):

        with self.lock:

            self.pending_msgs[msg_id] = {
                "node_id": node_id,
                "sent_at": datetime.utcnow(),
                "ack_at": None,
                "status": "SENT",
            }

    # -------------------------------------------------------
    # Tracking de ACK
    # -------------------------------------------------------
    def track_ack(self, msg_id):

        with self.lock:

            if msg_id in self.pending_msgs:

                self.pending_msgs[msg_id]["ack_at"] = datetime.utcnow()
                self.pending_msgs[msg_id]["status"] = "ACK"

                return True

            return False

    # -------------------------------------------------------
    # Extraer métricas de disco en GB
    # -------------------------------------------------------
    def _extract_disk_gb(self, metrics: dict):

        # formato antiguo
        disk = metrics.get("disk")

        if isinstance(disk, dict):

            if "total_gb" in disk or "used_gb" in disk or "free_gb" in disk:

                t = float(disk.get("total_gb") or 0)
                u = float(disk.get("used_gb") or 0)
                f = float(disk.get("free_gb") or 0)

                return t, u, f

        # formato nuevo
        disks = metrics.get("disks")

        if isinstance(disks, list) and disks and isinstance(disks[0], dict):

            d0 = disks[0]

            t_b = float(d0.get("total_bytes") or 0)
            u_b = float(d0.get("used_bytes") or 0)
            f_b = float(d0.get("free_bytes") or 0)

            return (t_b / BYTES_TO_GB), (u_b / BYTES_TO_GB), (f_b / BYTES_TO_GB)

        return 0.0, 0.0, 0.0

    # -------------------------------------------------------
    # Totales del cluster
    # -------------------------------------------------------
    def compute_totals(self):

        with self.lock:

            total = used = free = 0.0
            reporting = 0

            for node_id, node in self.nodes.items():

                m = node.get("metrics")

                if not m or node.get("status") != "UP":
                    continue

                t, u, f = self._extract_disk_gb(m)

                total += t
                used += u
                free += f

                reporting += 1

            util = (used / total * 100.0) if total > 0 else 0.0

            return {
                "total_gb": total,
                "used_gb": used,
                "free_gb": free,
                "util_percent": util,
                "reporting": reporting,
            }