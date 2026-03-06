"""
config.py
Carga configuracion desde .env del dashboard.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# Host del servidor TCP (para enviar comandos via HTTP admin)
SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_ADMIN_PORT: int = int(os.getenv("SERVER_ADMIN_PORT", "3001"))

EXPECTED_NODES: list[str] = [
    "LPZ-01", "SCZ-01", "CBBA-01", "ORU-01",
    "PTS-01", "CHQ-01", "TJA-01", "BEN-01", "PND-01",
]
