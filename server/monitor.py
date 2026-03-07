# Monitor del cluster
# Detecta:
# 1) Nodos que dejaron de reportar (DOWN)
# 2) Desincronización de hora entre cliente y servidor
# 3) Registro en log de nodos que dejaron de reportar

import threading
import time
from datetime import datetime
from config import REPORT_TIMEOUT, TIME_DRIFT_THRESHOLD


class MonitorThread(threading.Thread):

    def __init__(self, cluster_state):
        super().__init__()
        self.cluster_state = cluster_state
        self.daemon = True  # el hilo muere cuando el servidor termina

        # archivo log de nodos que dejaron de reportar
        self.log_file = "nodes_no_report.log"

        # evitar repetir logs del mismo nodo
        self.logged_down_nodes = set()

    # -------------------------------------------------
    # registrar nodo que dejó de reportar
    # -------------------------------------------------

    def log_node_down(self, node_id, data):

        region = data.get("region") or node_id
        addr = data.get("addr")

        ip = "-"
        if addr:
            ip = addr[0]

        hora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        line = f"{hora} | {region} | {ip} | NO_REPORTA\n"

        with open(self.log_file, "a") as f:
            f.write(line)

    # -------------------------------------------------
    # hilo principal del monitor
    # -------------------------------------------------

    def run(self):

        while True:

            # snapshot del estado actual del cluster
            snapshot = self.cluster_state.get_snapshot()

            # tiempo actual del servidor
            now = datetime.utcnow()

            for node_id, data in snapshot.items():

                last_seen = data.get("last_seen")
                client_time = data.get("client_time")

                # -------------------------------------------------
                # 1 Detectar nodos que dejaron de reportar
                # -------------------------------------------------

                if last_seen:

                    delta = (now - last_seen).total_seconds()

                    if delta > REPORT_TIMEOUT:

                        # si recién cayó
                        if node_id not in self.logged_down_nodes:

                            self.cluster_state.mark_down_if_timeout(node_id)

                            self.log_node_down(node_id, data)

                            self.logged_down_nodes.add(node_id)

                    else:
                        # si el nodo volvió a reportar lo quitamos del set
                        if node_id in self.logged_down_nodes:
                            self.logged_down_nodes.remove(node_id)

                # -------------------------------------------------
                # 2 Detectar inconsistencia de hora del nodo
                # -------------------------------------------------

                if client_time:

                    drift = abs((now - client_time).total_seconds())

                    if drift > TIME_DRIFT_THRESHOLD:

                        print(
                            f"[TIME WARNING] Nodo {node_id} tiene reloj desincronizado ({drift:.2f} segundos)"
                        )

                        # enviar notificación automática al nodo
                        try:
                            self.cluster_state.notify_config_update(
                                node_id,
                                "Actualización de configuración: sincronizar reloj del sistema"
                            )
                        except Exception as e:
                            print(
                                f"[MONITOR] No se pudo enviar actualización de configuración a {node_id}: {e}"
                            )

            # el monitor revisa cada 2 segundos
            time.sleep(2)