import sys
from pathlib import Path

# agrega /server al path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import sb

print("sb is None?", sb is None)
if sb:
    print(sb.table("nodes").select("*").limit(1).execute().data)