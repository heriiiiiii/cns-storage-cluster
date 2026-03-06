import os
import psycopg2
from psycopg2.extras import RealDictCursor

Q_DASHBOARD = """
select
  n.node_id,
  coalesce(n.node_name, n.node_id) as node_name,
  n.status,
  n.last_seen,

  r.server_received_at,
  (r.raw_payload->'disks'->0->>'disk_name') as disk_name,
  (r.raw_payload->'disks'->0->>'disk_type') as disk_type,
  (r.raw_payload->'disks'->0->>'total_bytes')::bigint as total_bytes,
  (r.raw_payload->'disks'->0->>'used_bytes')::bigint  as used_bytes,
  (r.raw_payload->'disks'->0->>'free_bytes')::bigint  as free_bytes

from nodes n
left join lateral (
  select *
  from reports rr
  where rr.node_id = n.node_id and rr.server_received_at is not null
  order by rr.server_received_at desc
  limit 1
) r on true
order by n.node_id;
"""

def main():
    # Usa la connection string de Supabase (Settings > Database > Connection string)
    dsn = os.environ["DATABASE_URL"]  # ejemplo: postgres://...
    with psycopg2.connect(dsn, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(Q_DASHBOARD)
            rows = cur.fetchall()

    for row in rows:
        print(row["node_id"], row["status"], row["disk_name"], row["used_bytes"], "/", row["total_bytes"])

if name == "main":
    main()