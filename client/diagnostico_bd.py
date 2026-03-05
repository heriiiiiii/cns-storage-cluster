from supabase import create_client

sb = create_client(
    "https://csmgwdlixlxjchgmrttx.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzbWd3ZGxpeGx4amNoZ21ydHR4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjU0NTI1NiwiZXhwIjoyMDg4MTIxMjU2fQ.45LcdF7qT0mulDf-Uz2uk7fMqx-ztf9CMPDgNkitTg0"
)

print("=== FILAS EN REPORTS ===")
try:
    r = sb.table("reports").select("*").limit(3).execute()
    print(r.data)
except Exception as e:
    print(f"Error: {e}")

print()
print("=== TEST INSERT UUID ===")
try:
    r = sb.table("reports").insert({
        "node_id": "56947f2e-35b8-4751-ab4e-16539fcb5810",
        "client_reported_at": "2026-03-03T17:00:00Z",
        "server_received_at": "2026-03-03T17:00:00Z",
        "interval_seconds": 10,
        "raw_payload": {}
    }).execute()
    print(f"EXITO: {r.data}")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=== TEST INSERT TEXTO LPZ-01 ===")
try:
    r = sb.table("reports").insert({
        "node_id": "LPZ-01",
        "client_reported_at": "2026-03-03T17:00:00Z",
        "server_received_at": "2026-03-03T17:00:00Z",
        "interval_seconds": 10,
        "raw_payload": {}
    }).execute()
    print(f"EXITO: {r.data}")
except Exception as e:
    print(f"ERROR: {e}")