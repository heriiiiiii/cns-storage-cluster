#aqui podremos ver el Estado global del cluster, como los nodos que estan activos, los archivos que se encuentran en cada nodo, etc.

import threading
from datetime import datetime

class ClusterState:
    def __init__(self):
        self.lock = threading.Lock()
        # node_id -> state
        self.nodes = {}
        # msg_id -> tracking
        self.pending_msgs = {}  # msg_id -> {node_id, sent_at, ack_at, status}

    def register_or_update_connection(self, node_id, region=None, conn=None, addr=None):
        """Registra un nodo o actualiza su conexión (reconexión)."""
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
                }
            else:
                # reconexión: reemplazar socket/addr
                self.nodes[node_id]["conn"] = conn
                self.nodes[node_id]["addr"] = addr
                if region:
                    self.nodes[node_id]["region"] = region
                self.nodes[node_id]["status"] = "UP"
                self.nodes[node_id]["last_seen"] = now

    def update_metrics(self, node_id, metrics):
        now = datetime.utcnow()
        with self.lock:
            if node_id not in self.nodes:
                # Si llegan metrics antes de hello, igual creamos entrada
                self.nodes[node_id] = {
                    "region": None,
                    "status": "UP",
                    "last_seen": now,
                    "metrics": metrics,
                    "conn": None,
                    "addr": None,
                }
            else:
                self.nodes[node_id]["metrics"] = metrics
                self.nodes[node_id]["last_seen"] = now
                self.nodes[node_id]["status"] = "UP"

    def mark_down_if_timeout(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]["status"] = "DOWN"

    def touch(self, node_id):
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id]["last_seen"] = datetime.utcnow()
                self.nodes[node_id]["status"] = "UP"

    def get_snapshot(self):
        with self.lock:
            # No devolvemos el socket real en snapshot para evitar uso inseguro fuera del lock
            snap = {}
            for k, v in self.nodes.items():
                snap[k] = {
                    "region": v.get("region"),
                    "status": v.get("status"),
                    "last_seen": v.get("last_seen"),
                    "metrics": v.get("metrics"),
                    "addr": v.get("addr"),
                }
            return snap

    def get_conn(self, node_id):
        with self.lock:
            node = self.nodes.get(node_id)
            return None if not node else node.get("conn")

    def track_message_sent(self, msg_id, node_id):
        with self.lock:
            self.pending_msgs[msg_id] = {
                "node_id": node_id,
                "sent_at": datetime.utcnow(),
                "ack_at": None,
                "status": "SENT",
            }

    def track_ack(self, msg_id):
        with self.lock:
            if msg_id in self.pending_msgs:
                self.pending_msgs[msg_id]["ack_at"] = datetime.utcnow()
                self.pending_msgs[msg_id]["status"] = "ACK"
                return True
            return False
        
    def compute_totals(self):
        with self.lock:
            total = 0.0
            used = 0.0
            free = 0.0
            reporting = 0
    
            for node_id, node in self.nodes.items():
                m = node.get("metrics")
                if not m or node.get("status") != "UP":
                    continue
                
                disk = (m.get("disk") or {})
                t = float(disk.get("total_gb") or 0)
                u = float(disk.get("used_gb") or 0)
                f = float(disk.get("free_gb") or 0)
    
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
                "reporting": reporting
            }