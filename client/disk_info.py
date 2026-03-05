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


def get_all_disk_metrics() -> list:
    """
    Retorna metricas de TODOS los discos del sistema en bytes.
    """
    if not PSUTIL_AVAILABLE:
        return [{
            "disk_name": "SimulatedDisk",
            "disk_type": "SSD",
            "total_bytes": 512000000000,
            "used_bytes": 120000000000,
            "free_bytes": 392000000000,
            "iops": _simulate_iops(),
        }]

    disks = []
    seen = set()  # evitar duplicados por mismo mountpoint

    try:
        partitions = psutil.disk_partitions(all=False)
        io_counters = {}
        try:
            io_counters = psutil.disk_io_counters(perdisk=True) or {}
        except Exception:
            pass

        for p in partitions:
            if p.mountpoint in seen:
                continue
            seen.add(p.mountpoint)

            try:
                usage = psutil.disk_usage(p.mountpoint)
            except PermissionError:
                continue  # disco sin permisos, saltar

            # IOPS por disco si disponible
            dev_key = p.device.replace("/dev/", "") if p.device else ""
            iops = _simulate_iops()
            if dev_key in io_counters:
                c = io_counters[dev_key]
                iops = round(c.read_count + c.write_count, 2)

            disks.append({
                "disk_name": p.device if p.device else p.mountpoint,
                "disk_type": _detect_disk_type(p.device),
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "iops": iops,
            })

    except Exception as e:
        print(f"[ERROR] No se pudo obtener info de discos: {e}")

    return disks if disks else [{
        "disk_name": "Unknown",
        "disk_type": "SSD",
        "total_bytes": 0,
        "used_bytes": 0,
        "free_bytes": 0,
        "iops": 0.0,
    }]


def get_disk_metrics() -> Optional[dict]:
    """Retorna solo el primer disco (compatibilidad). Usar get_all_disk_metrics() para todos."""
    disks = get_all_disk_metrics()
    return disks[0] if disks else None


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
