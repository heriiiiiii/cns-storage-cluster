# Monitor del cluster
# Detecta:
# 1) Nodos que dejaron de reportar (DOWN)
# 2) Desincronización de hora entre cliente y servidor

import threading
import time
from datetime import datetime
from config import REPORT_TIMEOUT, TIME_DRIFT_THRESHOLD


class MonitorThread(threading.Thread):

    def __init__(self, cluster_state):
        super().__init__()
        self.cluster_state = cluster_state
        self.daemon = True  # el hilo muere cuando el servidor termina

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

                if not last_seen:
                    continue

                delta = (now - last_seen).total_seconds()

                if delta > REPORT_TIMEOUT:
                    self.cluster_state.mark_down_if_timeout(node_id)

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