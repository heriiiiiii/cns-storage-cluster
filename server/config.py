# config.py

HOST = "0.0.0.0"
PORT = 3000
ADMIN_PORT = 3001

# tiempo máximo sin reportes antes de marcar nodo DOWN
REPORT_TIMEOUT = 15

# NUEVO: diferencia máxima permitida entre reloj cliente y servidor
TIME_DRIFT_THRESHOLD = 10


EXPECTED_NODES = {
    "LPZ-01", "SCZ-01", "CBBA-01", "ORU-01",
    "PTS-01", "CHQ-01", "TJA-01", "BEN-01", "PND-01"
}

# si False el servidor acepta cualquier nodo
ENFORCE_EXPECTED_NODES = False