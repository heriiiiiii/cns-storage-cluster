"""
gui.py
------
Interfaz grafica del cliente CNS usando tkinter (incluido en Python).
Muestra estado de conexion, metricas del disco y log de mensajes en tiempo real.
"""
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime, timezone

from config import NODE_CODE, SERVER_HOST, SERVER_PORT, INTERVAL_SECONDS
from disk_info import get_disk_metrics, get_extra_info


def bytes_to_gb(b):
    if b is None:
        return "N/A"
    return f"{b / (1024**3):.1f} GB"


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"CNS - Cliente Nodo: {NODE_CODE}")
        self.root.geometry("700x560")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)

        # Estado interno
        self._status = "DESCONECTADO"
        self._reports_sent = 0
        self._connection_thread = None
        self._running = False

        self._build_ui()
        self._refresh_disk_info()

    # ------------------------------------------------------------------
    # Construccion de la UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        BG      = "#1e1e2e"
        CARD    = "#2a2a3e"
        ACCENT  = "#7c3aed"
        GREEN   = "#22c55e"
        RED     = "#ef4444"
        YELLOW  = "#f59e0b"
        FG      = "#e2e8f0"
        SUBFG   = "#94a3b8"

        # ---- Header ----
        header = tk.Frame(self.root, bg=ACCENT, pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text=f"  CNS Monitor  —  Nodo: {NODE_CODE}",
                 bg=ACCENT, fg="white", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text=f"Servidor: {SERVER_HOST}:{SERVER_PORT}  |  Intervalo: {INTERVAL_SECONDS}s",
                 bg=ACCENT, fg="#ddd6fe", font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=12)

        # ---- Status bar ----
        status_frame = tk.Frame(self.root, bg=CARD, pady=8, padx=16)
        status_frame.pack(fill=tk.X, padx=12, pady=(10, 4))

        tk.Label(status_frame, text="Estado:", bg=CARD, fg=SUBFG,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.lbl_status = tk.Label(status_frame, text="DESCONECTADO",
                                   bg=CARD, fg=RED, font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=(6, 20))

        tk.Label(status_frame, text="Reportes enviados:", bg=CARD, fg=SUBFG,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.lbl_reports = tk.Label(status_frame, text="0", bg=CARD, fg=GREEN,
                                    font=("Segoe UI", 9, "bold"))
        self.lbl_reports.pack(side=tk.LEFT, padx=6)

        # Boton conectar/desconectar
        self.btn_connect = tk.Button(
            status_frame, text="  Conectar  ",
            bg=GREEN, fg="white", relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
            command=self._toggle_connection
        )
        self.btn_connect.pack(side=tk.RIGHT)

        # ---- Metricas de disco ----
        disk_outer = tk.LabelFrame(self.root, text=" Disco detectado ",
                                   bg=BG, fg=SUBFG,
                                   font=("Segoe UI", 9),
                                   bd=1, relief=tk.GROOVE)
        disk_outer.pack(fill=tk.X, padx=12, pady=4)

        disk_grid = tk.Frame(disk_outer, bg=BG)
        disk_grid.pack(fill=tk.X, padx=10, pady=8)

        labels = ["Dispositivo", "Tipo", "Total", "Usado", "Libre", "% Uso", "IOPS"]
        self.disk_vals = {}
        for i, lbl in enumerate(labels):
            tk.Label(disk_grid, text=lbl, bg=BG, fg=SUBFG,
                     font=("Segoe UI", 8)).grid(row=0, column=i, padx=8)
            val = tk.Label(disk_grid, text="—", bg=CARD, fg=FG,
                           font=("Segoe UI", 9, "bold"), width=10, pady=4)
            val.grid(row=1, column=i, padx=8, pady=2)
            self.disk_vals[lbl] = val

        # Barra de uso
        bar_frame = tk.Frame(disk_outer, bg=BG)
        bar_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        tk.Label(bar_frame, text="Uso:", bg=BG, fg=SUBFG,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(bar_frame, length=580, mode="determinate")
        self.progress.pack(side=tk.LEFT, padx=6)

        # ---- Extra info ----
        extra_frame = tk.Frame(self.root, bg=BG)
        extra_frame.pack(fill=tk.X, padx=12, pady=2)

        self.lbl_ip  = tk.Label(extra_frame, text="IP: —", bg=BG, fg=SUBFG,
                                font=("Segoe UI", 8))
        self.lbl_ip.pack(side=tk.LEFT, padx=(0, 20))
        self.lbl_mac = tk.Label(extra_frame, text="MAC: —", bg=BG, fg=SUBFG,
                                font=("Segoe UI", 8))
        self.lbl_mac.pack(side=tk.LEFT, padx=(0, 20))
        self.lbl_ram = tk.Label(extra_frame, text="RAM: —", bg=BG, fg=SUBFG,
                                font=("Segoe UI", 8))
        self.lbl_ram.pack(side=tk.LEFT)

        # ---- Log de mensajes ----
        log_frame = tk.LabelFrame(self.root, text=" Log de mensajes del servidor ",
                                  bg=BG, fg=SUBFG,
                                  font=("Segoe UI", 9),
                                  bd=1, relief=tk.GROOVE)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=8,
            bg="#0f0f1a", fg="#a5f3fc",
            font=("Consolas", 8),
            insertbackground="white",
            state=tk.DISABLED, bd=0
        )
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._log("Sistema listo. Presiona 'Conectar' para iniciar.")

    # ------------------------------------------------------------------
    # Helpers de UI
    # ------------------------------------------------------------------
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _set_status(self, text: str, color: str):
        self.lbl_status.configure(text=text, fg=color)

    def _refresh_disk_info(self):
        disk = get_disk_metrics()
        extra = get_extra_info()

        if disk:
            total = disk["total_bytes"]
            used  = disk["used_bytes"]
            free  = disk["free_bytes"]
            pct   = round(used / total * 100, 1) if total > 0 else 0

            self.disk_vals["Dispositivo"].configure(text=disk["disk_name"][:12])
            self.disk_vals["Tipo"].configure(text=disk["disk_type"])
            self.disk_vals["Total"].configure(text=bytes_to_gb(total))
            self.disk_vals["Usado"].configure(text=bytes_to_gb(used))
            self.disk_vals["Libre"].configure(text=bytes_to_gb(free))
            self.disk_vals["% Uso"].configure(text=f"{pct}%",
                fg="#ef4444" if pct > 80 else "#f59e0b" if pct > 60 else "#22c55e")
            self.disk_vals["IOPS"].configure(text=str(int(disk["iops"])))
            self.progress["value"] = pct

        if extra:
            self.lbl_ip.configure(text=f"IP: {extra.get('ip','—')}")
            self.lbl_mac.configure(text=f"MAC: {extra.get('mac','—')}")
            ram_total = bytes_to_gb(extra.get("ram_total_bytes"))
            ram_used  = bytes_to_gb(extra.get("ram_used_bytes"))
            self.lbl_ram.configure(text=f"RAM: {ram_used} / {ram_total}")

        # Refrescar cada 5s
        self.root.after(5000, self._refresh_disk_info)

    # ------------------------------------------------------------------
    # Control de conexion
    # ------------------------------------------------------------------
    def _toggle_connection(self):
        if not self._running:
            self._start_client()
        else:
            self._stop_client()

    def _start_client(self):
        self._running = True
        self.btn_connect.configure(text="  Detener  ", bg="#ef4444")
        self._connection_thread = threading.Thread(
            target=self._run_client_thread, daemon=True
        )
        self._connection_thread.start()

    def _stop_client(self):
        self._running = False
        self.btn_connect.configure(text="  Conectar  ", bg="#22c55e")
        self._set_status("DESCONECTADO", "#ef4444")
        self._log("Cliente detenido por el usuario.")

    def _run_client_thread(self):
        """Corre en hilo separado para no bloquear la UI."""
        import socket as sock_mod
        import time
        from report_builder import build_report
        from message_handler import handle_server_message
        from config import RECONNECT_WAIT, INTERVAL_SECONDS

        NEWLINE = chr(10)

        while self._running:
            # Intentar conectar
            self.root.after(0, lambda: self._set_status("CONECTANDO...", "#f59e0b"))
            self._log(f"Conectando a {SERVER_HOST}:{SERVER_PORT}...")

            try:
                sock = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
                sock.connect((SERVER_HOST, SERVER_PORT))
            except (ConnectionRefusedError, OSError) as e:
                self._log(f"Sin conexion: {e}. Reintentando en {RECONNECT_WAIT}s...")
                time.sleep(RECONNECT_WAIT)
                continue

            self.root.after(0, lambda: self._set_status("CONECTADO", "#22c55e"))
            self._log("Conexion establecida con el servidor.")

            # Hilo de recepcion
            def recv_loop(s):
                buf = ""
                while self._running:
                    try:
                        chunk = s.recv(4096).decode("utf-8")
                        if not chunk:
                            break
                        buf += chunk
                        while NEWLINE in buf:
                            line, buf = buf.split(NEWLINE, 1)
                            line = line.strip()
                            if line:
                                handle_server_message(line, s)
                                self.root.after(0, lambda l=line: self._on_server_msg(l))
                    except Exception:
                        break

            threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()

            # Bucle de envio
            try:
                while self._running:
                    report_json = build_report()
                    if report_json:
                        sock.sendall((report_json + NEWLINE).encode("utf-8"))
                        self._reports_sent += 1
                        count = self._reports_sent
                        self.root.after(0, lambda c=count: self.lbl_reports.configure(text=str(c)))
                        self._log(f"Reporte #{self._reports_sent} enviado.")
                    time.sleep(INTERVAL_SECONDS)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                self._log(f"Conexion perdida: {e}. Reconectando...")
                self.root.after(0, lambda: self._set_status("RECONECTANDO", "#f59e0b"))
                try:
                    sock.close()
                except Exception:
                    pass
                time.sleep(RECONNECT_WAIT)

        try:
            sock.close()
        except Exception:
            pass

    def _on_server_msg(self, raw: str):
        try:
            data = json.loads(raw)
            content = data.get("content", raw)
        except Exception:
            content = raw
        self._log(f"[SERVIDOR] {content}")


def launch_gui():
    root = tk.Tk()
    app = ClientGUI(root)
    root.mainloop()
