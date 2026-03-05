"""
gui.py
Interfaz grafica del cliente CNS usando tkinter.
Muestra TODOS los discos del sistema en una tabla con scroll.
"""
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

from config import NODE_CODE, SERVER_HOST, SERVER_PORT, INTERVAL_SECONDS
from disk_info import get_all_disk_metrics, get_extra_info

BG    = "#1e1e2e"
CARD  = "#2a2a3e"
ACCENT= "#7c3aed"
GREEN = "#22c55e"
RED   = "#ef4444"
AMBER = "#f59e0b"
FG    = "#e2e8f0"
SUBFG = "#94a3b8"
CYAN  = "#a5f3fc"

def bytes_to_gb(b):
    if not b:
        return "0.0 GB"
    return f"{b / (1024**3):.1f} GB"

def pct_color(p):
    if p > 80: return RED
    if p > 60: return AMBER
    return GREEN


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"CNS — Nodo: {NODE_CODE}")
        self.root.geometry("780x620")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self._reports_sent = 0
        self._running = False
        self._build_ui()
        self._refresh_disks()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=ACCENT, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"  CNS Monitor  —  Nodo: {NODE_CODE}",
                 bg=ACCENT, fg="white", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
        tk.Label(hdr, text=f"{SERVER_HOST}:{SERVER_PORT}  |  cada {INTERVAL_SECONDS}s",
                 bg=ACCENT, fg="#ddd6fe", font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=12)

        # Status bar
        sb = tk.Frame(self.root, bg=CARD, pady=8, padx=16)
        sb.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(sb, text="Estado:", bg=CARD, fg=SUBFG, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.lbl_status = tk.Label(sb, text="DESCONECTADO", bg=CARD, fg=RED,
                                   font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=(6, 20))
        tk.Label(sb, text="Reportes:", bg=CARD, fg=SUBFG, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.lbl_reports = tk.Label(sb, text="0", bg=CARD, fg=GREEN,
                                    font=("Segoe UI", 9, "bold"))
        self.lbl_reports.pack(side=tk.LEFT, padx=(4, 0))
        self.btn = tk.Button(sb, text="  Conectar  ", bg=GREEN, fg="white",
                             relief=tk.FLAT, font=("Segoe UI", 9, "bold"),
                             cursor="hand2", command=self._toggle)
        self.btn.pack(side=tk.RIGHT)

        # Extra info
        ef = tk.Frame(self.root, bg=BG)
        ef.pack(fill=tk.X, padx=14, pady=(2, 0))
        self.lbl_ip  = tk.Label(ef, text="IP: —",  bg=BG, fg=SUBFG, font=("Segoe UI", 8))
        self.lbl_ip.pack(side=tk.LEFT, padx=(0, 16))
        self.lbl_mac = tk.Label(ef, text="MAC: —", bg=BG, fg=SUBFG, font=("Segoe UI", 8))
        self.lbl_mac.pack(side=tk.LEFT, padx=(0, 16))
        self.lbl_ram = tk.Label(ef, text="RAM: —", bg=BG, fg=SUBFG, font=("Segoe UI", 8))
        self.lbl_ram.pack(side=tk.LEFT)

        # Tabla de discos
        disk_frame = tk.LabelFrame(self.root, text=" Discos detectados ",
                                   bg=BG, fg=SUBFG, font=("Segoe UI", 9),
                                   bd=1, relief=tk.GROOVE)
        disk_frame.pack(fill=tk.BOTH, expand=False, padx=12, pady=(6, 4))

        cols = ("Dispositivo", "Tipo", "Total", "Usado", "Libre", "% Uso", "IOPS")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Discos.Treeview",
                        background=CARD, foreground=FG,
                        fieldbackground=CARD, rowheight=26,
                        font=("Segoe UI", 9))
        style.configure("Discos.Treeview.Heading",
                        background=ACCENT, foreground="white",
                        font=("Segoe UI", 9, "bold"))
        style.map("Discos.Treeview", background=[("selected", "#3b3b5c")])

        self.tree = ttk.Treeview(disk_frame, columns=cols, show="headings",
                                 height=5, style="Discos.Treeview")
        widths = [130, 60, 90, 90, 90, 70, 90]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(disk_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,0), pady=6)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=6, padx=(0,6))

        # Tags de color por uso
        self.tree.tag_configure("ok",   foreground=GREEN)
        self.tree.tag_configure("warn", foreground=AMBER)
        self.tree.tag_configure("crit", foreground=RED)

        # Log
        lf = tk.LabelFrame(self.root, text=" Log de mensajes del servidor ",
                            bg=BG, fg=SUBFG, font=("Segoe UI", 9),
                            bd=1, relief=tk.GROOVE)
        lf.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))
        self.log_box = scrolledtext.ScrolledText(
            lf, height=7, bg="#0f0f1a", fg=CYAN,
            font=("Consolas", 8), insertbackground="white",
            state=tk.DISABLED, bd=0)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._log("Sistema listo. Presiona 'Conectar' para iniciar.")

    # ---------------------------------------------------------------- helpers
    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _set_status(self, text, color):
        self.lbl_status.configure(text=text, fg=color)

    def _refresh_disks(self):
        disks = get_all_disk_metrics()
        extra = get_extra_info()

        # Limpiar tabla
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Insertar cada disco
        for d in disks:
            total = d["total_bytes"]
            used  = d["used_bytes"]
            free  = d["free_bytes"]
            pct   = round(used / total * 100, 1) if total > 0 else 0.0
            tag   = "crit" if pct > 80 else "warn" if pct > 60 else "ok"
            self.tree.insert("", tk.END, values=(
                d["disk_name"][:18],
                d["disk_type"],
                bytes_to_gb(total),
                bytes_to_gb(used),
                bytes_to_gb(free),
                f"{pct}%",
                f"{int(d['iops']):,}",
            ), tags=(tag,))

        # Extra info
        if extra:
            self.lbl_ip.configure(text=f"IP: {extra.get('ip','—')}")
            self.lbl_mac.configure(text=f"MAC: {extra.get('mac','—')}")
            rt = bytes_to_gb(extra.get("ram_total_bytes"))
            ru = bytes_to_gb(extra.get("ram_used_bytes"))
            self.lbl_ram.configure(text=f"RAM: {ru} / {rt}")

        self.root.after(5000, self._refresh_disks)

    # --------------------------------------------------------- conexion
    def _toggle(self):
        if not self._running:
            self._running = True
            self.btn.configure(text="  Detener  ", bg=RED)
            threading.Thread(target=self._run_client, daemon=True).start()
        else:
            self._running = False
            self.btn.configure(text="  Conectar  ", bg=GREEN)
            self._set_status("DESCONECTADO", RED)
            self._log("Cliente detenido.")

    def _run_client(self):
        import socket as sm, time
        from report_builder import build_report
        from message_handler import handle_server_message
        from config import RECONNECT_WAIT, INTERVAL_SECONDS
        NL = chr(10)

        while self._running:
            self.root.after(0, lambda: self._set_status("CONECTANDO...", AMBER))
            self._log(f"Conectando a {SERVER_HOST}:{SERVER_PORT}...")
            try:
                sock = sm.socket(sm.AF_INET, sm.SOCK_STREAM)
                sock.connect((SERVER_HOST, SERVER_PORT))
            except (ConnectionRefusedError, OSError) as e:
                self._log(f"Sin conexion: {e}. Reintentando en {RECONNECT_WAIT}s...")
                time.sleep(RECONNECT_WAIT)
                continue

            self.root.after(0, lambda: self._set_status("CONECTADO", GREEN))
            self._log("Conexion establecida.")

            def recv_loop(s):
                buf = ""
                while self._running:
                    try:
                        chunk = s.recv(4096).decode("utf-8")
                        if not chunk: break
                        buf += chunk
                        while NL in buf:
                            line, buf = buf.split(NL, 1)
                            line = line.strip()
                            if line:
                                handle_server_message(line, s)
                                self.root.after(0, lambda l=line: self._on_server_msg(l))
                    except Exception:
                        break

            threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()

            try:
                while self._running:
                    report = build_report()
                    if report:
                        sock.sendall((report + NL).encode("utf-8"))
                        self._reports_sent += 1
                        c = self._reports_sent
                        self.root.after(0, lambda x=c: self.lbl_reports.configure(text=str(x)))
                        self._log(f"Reporte #{self._reports_sent} enviado ({len(build_report() or '')} bytes).")
                    time.sleep(INTERVAL_SECONDS)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                self._log(f"Conexion perdida: {e}. Reconectando...")
                self.root.after(0, lambda: self._set_status("RECONECTANDO", AMBER))
                try: sock.close()
                except: pass
                time.sleep(RECONNECT_WAIT)

        try: sock.close()
        except: pass

    def _on_server_msg(self, raw):
        try:
            content = json.loads(raw).get("content", raw)
        except Exception:
            content = raw
        self._log(f"[SERVIDOR] {content}")


def launch_gui():
    root = tk.Tk()
    ClientGUI(root)
    root.mainloop()
