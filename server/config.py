# config.py
HOST = "0.0.0.0"
PORT = 3000
ADMIN_PORT = 3001
REPORT_TIMEOUT = 15

EXPECTED_NODES = {
    "LPZ-01", "SCZ-01", "CBBA-01", "ORU-01",
    "PTS-01", "CHQ-01", "TJA-01", "BEN-01", "PND-01"
}

# ✅ nuevo: si False, el servidor acepta cualquier node_id/node_code
ENFORCE_EXPECTED_NODES = False