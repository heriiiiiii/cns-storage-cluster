"""
logger.py
---------
Maneja el registro de mensajes del servidor en archivo .log.
Backlog item 9: Guardar mensajes recibidos en archivo .log
"""

import os
from datetime import datetime, timezone
from config import LOG_FILE


def log_server_message(content: str, message_id: str = "") -> None:
    """
    Agrega un mensaje del servidor al archivo client.log.
    Nunca sobreescribe, siempre hace append.

    Formato de cada linea:
    [2026-03-03T12:00:00+00:00] [ID: abc123] Contenido del mensaje
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    id_part = f"[ID: {message_id}] " if message_id else ""
    line = f"[{timestamp}] {id_part}{content}\n"

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except IOError as e:
        print(f"[ERROR] No se pudo escribir en {LOG_FILE}: {e}")
