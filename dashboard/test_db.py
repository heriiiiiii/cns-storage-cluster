from src.queries import get_dashboard_rows

rows = get_dashboard_rows()
print("rows:", len(rows))
for r in rows[:5]:
    print(r["node_id"], r["status"], r.get("disk_name"), r.get("used_bytes"), "/", r.get("total_bytes"))