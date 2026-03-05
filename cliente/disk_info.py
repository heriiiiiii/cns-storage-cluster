"""
disk_info.py
Recolecta metricas reales del disco y datos extra del sistema.
Items 3 (discos), 4 (timestamp), 11 (extra: IP, MAC, RAM).

CONTRATO: usa bytes (total_bytes, used_bytes, free_bytes) segun BD del servidor.
"""
import platform
import random
import socket
import uuid
from datetime import datetime, timezone
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[ADVERTENCIA] Instala psutil: pip install psutil")


def _detect_disk_type(device: str) -> str:
    try:
        if platform.system() == "Linux":
            dev_name = device.replace("/dev/", "").rstrip("0123456789")
            with open(f"/sys/block/{dev_name}/queue/rotational") as f:
                return "HDD" if f.read().strip() == "1" else "SSD"
    except Exception:
        pass
    return "SSD"


def _simulate_iops() -> float:
    return round(random.uniform(800.0, 2000.0), 2)


def get_disk_metrics() -> Optional[dict]:
    """
    Retorna metricas del primer disco en bytes (contrato del servidor).
    """
    if not PSUTIL_AVAILABLE:
        return {
            "disk_name": "SimulatedDisk",
            "disk_type": "SSD",
            "total_bytes": 512000000000,
            "used_bytes": 120000000000,
            "free_bytes": 392000000000,
            "iops": _simulate_iops(),
        }

    try:
        partitions = psutil.disk_partitions(all=False)
        if not partitions:
            return None

        target = None
        for p in partitions:
            if p.mountpoint in ("/", "C:\\"):
                target = p
                break
        if target is None:
            target = partitions[0]

        usage = psutil.disk_usage(target.mountpoint)

        iops = _simulate_iops()
        try:
            counters = psutil.disk_io_counters(perdisk=False)
            if counters:
                iops = round(counters.read_count + counters.write_count, 2)
        except Exception:
            pass

        return {
            "disk_name": target.device if target.device else target.mountpoint,
            "disk_type": _detect_disk_type(target.device),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "iops": iops,
        }

    except Exception as e:
        print(f"[ERROR] No se pudo obtener info del disco: {e}")
        return None


def get_report_timestamp() -> str:
    """ISO 8601 UTC sin microsegundos, ej: 2026-03-03T12:00:00Z"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_extra_info() -> dict:
    """
    Retorna datos extra del sistema: IP, MAC, RAM.
    Item 11: estructura preparada para futuras modificaciones.
    """
    extra = {
        "ip": None,
        "mac": None,
        "ram_total_bytes": None,
        "ram_used_bytes": None,
    }

    # IP local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        extra["ip"] = s.getsockname()[0]
        s.close()
    except Exception:
        extra["ip"] = "127.0.0.1"

    # MAC address
    try:
        mac_int = uuid.getnode()
        mac_str = ":".join(
            f"{(mac_int >> (i * 8)) & 0xFF:02X}" for i in reversed(range(6))
        )
        extra["mac"] = mac_str
    except Exception:
        extra["mac"] = "00:00:00:00:00:00"

    # RAM
    if PSUTIL_AVAILABLE:
        try:
            ram = psutil.virtual_memory()
            extra["ram_total_bytes"] = ram.total
            extra["ram_used_bytes"] = ram.used
        except Exception:
            pass

    return extra
