"""
config.py
---------
Carga la configuración desde el archivo .env.
Todos los parámetros configurables del cliente están aquí.
"""

import os
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()

# Identificador del nodo
NODE_CODE: str = os.getenv("NODE_CODE", "LPZ-01")

# Conexión TCP al servidor central
SERVER_HOST: str = os.getenv("SERVER_HOST", "192.168.0.6")
SERVER_PORT: int = int(os.getenv("SERVER_PORT", "5000"))

# Comportamiento del cliente
INTERVAL_SECONDS: int = int(os.getenv("INTERVAL_SECONDS", "10"))
RECONNECT_WAIT: int = int(os.getenv("RECONNECT_WAIT", "5"))

# Archivo de log para mensajes del servidor
LOG_FILE: str = "client.log"
