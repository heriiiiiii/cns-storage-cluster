"""
connection.py
Gestiona la conexion TCP al servidor central.
Items: 2 (conexion TCP), 6 (envio periodico), 7 (reconexion), 8 (recepcion mensajes)
"""
import socket
import threading
import time
from config import SERVER_HOST, SERVER_PORT, INTERVAL_SECONDS, RECONNECT_WAIT, NODE_CODE
from report_builder import build_report
from message_handler import handle_server_message

NEWLINE = chr(10)  # salto de linea para delimitador de mensajes


def _receive_loop(sock):
    """Hilo que escucha mensajes entrantes del servidor continuamente."""
    buffer = ""
    while True:
        try:
            chunk = sock.recv(4096).decode("utf-8")
            if not chunk:
                print("[INFO] Servidor cerro la conexion.")
                break
            buffer += chunk
            while NEWLINE in buffer:
                line, buffer = buffer.split(NEWLINE, 1)
                line = line.strip()
                if line:
                    handle_server_message(line, sock)
        except Exception as e:
            print(f"[INFO] Hilo de recepcion finalizado: {e}")
            break


def _connect():
    """Intenta conectar al servidor, reintenta infinitamente hasta lograrlo."""
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((SERVER_HOST, SERVER_PORT))
            print(f"[OK] Conectado a {SERVER_HOST}:{SERVER_PORT} como {repr(NODE_CODE)}")
            return sock
        except (ConnectionRefusedError, OSError) as e:
            print(f"[RECONEXION] Servidor no disponible ({e}). Reintentando en {RECONNECT_WAIT}s...")
            time.sleep(RECONNECT_WAIT)


def run_client():
    """Bucle principal: conecta, lanza hilo de recepcion, envia reportes periodicamente."""
    while True:
        sock = _connect()
        recv_thread = threading.Thread(target=_receive_loop, args=(sock,), daemon=True)
        recv_thread.start()
        try:
            while True:
                report_json = build_report()
                if report_json:
                    sock.sendall((report_json + NEWLINE).encode("utf-8"))
                    print("[ENVIADO] Reporte enviado correctamente.")
                else:
                    print("[AVISO] Reporte vacio, no se envio.")
                time.sleep(INTERVAL_SECONDS)
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"[ERROR] Conexion perdida: {e}. Reconectando...")
            try:
                sock.close()
            except Exception:
                pass
            time.sleep(RECONNECT_WAIT)
