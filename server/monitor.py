#Esto sera un detector de nodos DOWN

import threading
import time
from datetime import datetime
from config import REPORT_TIMEOUT

class MonitorThread(threading.Thread):
    def __init__(self, cluster_state):
        super().__init__()
        self.cluster_state = cluster_state
        self.daemon = True

    def run(self):
        while True:
            snapshot = self.cluster_state.get_snapshot()
            now = datetime.utcnow()

            for node_id, data in snapshot.items():
                last_seen = data["last_seen"]
                if not last_seen:
                    continue
                delta = (now - last_seen).total_seconds()
                if delta > REPORT_TIMEOUT:
                    self.cluster_state.mark_down_if_timeout(node_id)

            time.sleep(2)