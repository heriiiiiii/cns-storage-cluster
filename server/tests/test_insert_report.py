import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone
from db import insert_report, upsert_node

def iso_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# 1) Upsert node
upsert_node(
    node_id="PRUEBITA-01-RUDDY",
    status="ACTIVE",
    last_seen=iso_utc(),
    addr="127.0.0.1:9999",
    node_name="Nodo de Prueba"
)

# 2) Insert report (con payload parecido al real)
payload = {
    "type": "REPORT",
    "node_code": "PRUEBITA-01-RUDDY",
    "client_reported_at": iso_utc(),
    "interval_seconds": 10,
    "disks": [{
        "disk_name": "C:\\",
        "disk_type": "SSD",
        "total_bytes": 500_000_000_000,
        "used_bytes": 200_000_000_000,
        "free_bytes": 300_000_000_000,
        "iops": 1234
    }],
    "extra": {"ip": "127.0.0.1"}
}

res = insert_report(
    node_id="PRUEBITA-01-RUDDY",
    client_reported_at=payload["client_reported_at"],
    server_received_at=iso_utc(),
    interval_seconds=payload["interval_seconds"],
    raw_payload=payload
)

print("insert_report result:", res.data if res else None)
print("OK")