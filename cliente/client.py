"""
client.py
Punto de entrada principal del cliente CNS.
Ejecutar sin argumentos: abre la interfaz grafica.
Ejecutar con --cli: modo consola (sin GUI).
"""
import sys
from config import NODE_CODE, SERVER_HOST, SERVER_PORT, INTERVAL_SECONDS

SEP = "=" * 50

def run_cli():
    """Modo consola, sin interfaz grafica."""
    print(SEP)
    print(" CLIENTE CNS - Nodo Regional")
    print(SEP)
    print(f" Nodo      : {NODE_CODE}")
    print(f" Servidor  : {SERVER_HOST}:{SERVER_PORT}")
    print(f" Intervalo : {INTERVAL_SECONDS}s")
    print(f" Modo      : CLI (consola)")
    print(SEP)
    print()
    from connection import run_client
    try:
        run_client()
    except KeyboardInterrupt:
        print("[INFO] Cliente detenido manualmente.")
        sys.exit(0)

def run_gui():
    """Modo interfaz grafica (default)."""
    try:
        from gui import launch_gui
        launch_gui()
    except ImportError as e:
        print(f"[ERROR] No se pudo cargar la GUI: {e}")
        print("[INFO] Iniciando en modo CLI...")
        run_cli()

if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        run_gui()
