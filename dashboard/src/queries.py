from .db import fetch_all

# 1 fila por nodo:
# - toma el último registro de disk_metrics asociado al último report del nodo
# - si un nodo no tiene reportes/metrics, devuelve nulls en disco (pero igual lista el nodo)
Q_DASHBOARD = """
select
  n.node_id,
  coalesce(n.node_name, n.node_id) as node_name,
  n.status,
  n.last_seen,

  dm.server_received_at,
  dm.disk_name,
  dm.disk_type,
  dm.total_bytes,
  dm.used_bytes,
  dm.free_bytes,
  dm.iops

from nodes n
left join lateral (
  select
    rr.server_received_at,
    dmm.disk_name,
    dmm.disk_type,
    dmm.total_bytes,
    dmm.used_bytes,
    dmm.free_bytes,
    dmm.iops
  from reports rr
  join disk_metrics dmm on dmm.report_id = rr.id
  where rr.node_id = n.node_id
  order by rr.server_received_at desc nulls last
  limit 1
) dm on true
order by n.node_id;
"""

def get_dashboard_rows():
    return fetch_all(Q_DASHBOARD)