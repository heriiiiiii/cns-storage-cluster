# config.py
HOST = "0.0.0.0"
PORT = 3000
REPORT_TIMEOUT = 15

EXPECTED_NODES = {
    "LPZ", "SCZ", "CBBA", "ORU",
    "PTS", "CHQ", "TJA", "BEN", "PND"
}

# ✅ nuevo: si False, el servidor acepta cualquier node_id/node_code
ENFORCE_EXPECTED_NODES = False