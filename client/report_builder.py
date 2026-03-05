"""
report_builder.py
Construye el JSON oficial del reporte segun el contrato definido por el servidor.
Item 5: JSON oficial. Item 11: seccion extra con IP, MAC, RAM.
"""
import json
from typing import Optional
from disk_info import get_disk_metrics, get_report_timestamp, get_extra_info
from config import NODE_CODE, INTERVAL_SECONDS


def build_report() -> Optional[str]:
    """
    Construye el JSON de reporte en el formato exacto esperado por el servidor:

    {
        "type": "REPORT",
        "node_code": "LPZ-01",
        "client_reported_at": "2026-03-03T12:00:00Z",
        "interval_seconds": 10,
        "disks": [
            {
                "disk_name": "C:\\",
                "disk_type": "SSD",
                "total_bytes": 512000000000,
                "used_bytes": 200000000000,
                "free_bytes": 312000000000,
                "iops": 1500
            }
        ],
        "extra": {
            "ip": "192.168.0.50",
            "mac": "AA:BB:CC:DD:EE:FF",
            "ram_total_bytes": 17179869184,
            "ram_used_bytes": 8589934592
        }
    }
    """
    disk = get_disk_metrics()
    if disk is None:
        print("[ERROR] No se pudo obtener metricas del disco.")
        return None

    report = {
        "type": "REPORT",
        "node_code": NODE_CODE,
        "client_reported_at": get_report_timestamp(),
        "interval_seconds": INTERVAL_SECONDS,
        "disks": [disk],
        "extra": get_extra_info(),
    }

    try:
        json_str = json.dumps(report, ensure_ascii=False)
        json.loads(json_str)
        return json_str
    except (TypeError, ValueError) as e:
        print(f"[ERROR] JSON mal formado: {e}")
        return None
