from supabase import create_client

sb = create_client(
    'https://csmgwdlixlxjchgmrttx.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNzbWd3ZGxpeGx4amNoZ21ydHR4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjU0NTI1NiwiZXhwIjoyMDg4MTIxMjU2fQ.45LcdF7qT0mulDf-Uz2uk7fMqx-ztf9CMPDgNkitTg0'
)

print("=== TABLA NODES ===")
nodes = sb.table('nodes').select('*').execute()
for n in nodes.data:
    print(n)
