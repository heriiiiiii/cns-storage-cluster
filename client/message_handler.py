"""
message_handler.py
Maneja recepcion de mensajes del servidor y envio de ACK.
Items: 8 (recepcion mensajes), 10 (ACK)
"""
import json
import socket
from logger import log_server_message

NEWLINE = chr(10)


def handle_server_message(raw_message, sock):
    """
    Procesa mensaje entrante del servidor:
      1. Parsea JSON
      2. Muestra en consola
      3. Guarda en client.log
      4. Envia ACK

    Formato esperado:
    {"type": "server_message", "message_id": "uuid...", "content": "Reinicie servicio"}
    """
    try:
        data = json.loads(raw_message)
    except json.JSONDecodeError:
        print(f"[AVISO] Mensaje no es JSON valido: {repr(raw_message)}")
        return

    message_id = data.get("message_id", "")
    content    = data.get("content", raw_message)

    # Mostrar en consola
    print(f"[SERVIDOR] {content}")

    # Guardar en log (item 9)
    log_server_message(content, message_id)

    # Enviar ACK (item 10)
    if message_id:
        ack = json.dumps({"type": "ACK", "message_id": message_id})
        try:
            sock.sendall((ack + NEWLINE).encode("utf-8"))
            print(f"[ACK enviado] message_id={message_id}")
        except Exception as e:
            print(f"[ERROR] No se pudo enviar ACK: {e}")
