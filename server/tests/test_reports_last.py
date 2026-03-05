import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import sb

r = sb.table("reports").select("*").order("server_received_at", desc=True).limit(5).execute()
print("ULTIMOS REPORTS:")
for row in r.data:
    print(row.get("node_id"), row.get("server_received_at"))