import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import threading
import time
import os
import shutil
import ctypes
import subprocess
from pathlib import Path

from bot360_app.common.settings import (
    ALERTS_LOG_PATH,
    load_main_config,
    save_main_config,
    BASE_DIR,
)

from __version__ import __version__ as VERSION_ACTUAL, RELEASE_TAG  # noqa: F401

PLANTILLA_PATH = BASE_DIR / "usuario" / "PLANTILLA_ACTUALIZADA.csv"
UPDATE_CHECK_URL = "https://api.github.com/repos/PabloGra77/BOT-HC/releases/latest"


class AdminPanelApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"BOT360 v{VERSION_ACTUAL} - Panel de Control")
        self.root.geometry("950x780")
        self.root.resizable(True, True)

        self.maintenance_mode = tk.BooleanVar()
        self.keep_awake = tk.BooleanVar(value=False)
        self.last_log_size = 0

        # Dashboard stats
        self.total_descargados = tk.IntVar(value=0)
        self.total_pendientes = tk.IntVar(value=0)
        self.ultima_descarga = tk.StringVar(value="—")

        self._selected_hc_index = None

        self.setup_ui()
        self.load_config()

        self.monitor_thread = threading.Thread(target=self.monitor_alerts, daemon=True)
        self.monitor_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ─────────────────────────────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────────────────────────────
    def setup_ui(self):
        # Top status bar
        top_frame = ttk.Frame(self.root, padding=(10, 6))
        top_frame.pack(fill="x")

        self.lbl_status = ttk.Label(top_frame, text="Estado: Cargando...", font=("Arial", 11, "bold"))
        self.lbl_status.pack(side="left")

        ttk.Button(top_frame, text="⚡ Activar/Desactivar Mantenimiento",
                   command=self.toggle_maintenance).pack(side="right", padx=5)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10)

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=8)

        self._build_tab_dashboard(self.notebook)
        self._build_tab_credenciales(self.notebook)
        self._build_tab_herramientas(self.notebook)
        self._build_tab_logs(self.notebook)

    # ── TAB DASHBOARD ─────────────────────────────────────────────────────────
    def _build_tab_dashboard(self, nb):
        frame = ttk.Frame(nb, padding=10)
        nb.add(frame, text="  Dashboard  ")

        # Stats cards
        stats_frame = ttk.LabelFrame(frame, text="Estadísticas de Descarga", padding=12)
        stats_frame.pack(fill="x", pady=(0, 12))

        for col_data in [
            ("HCs Descargadas", self.total_descargados, "#27ae60"),
            ("HCs Pendientes",  self.total_pendientes,  "#e67e22"),
        ]:
            col = ttk.Frame(stats_frame)
            col.pack(side="left", expand=True)
            ttk.Label(col, text=col_data[0], font=("Arial", 9)).pack()
            ttk.Label(col, textvariable=col_data[1],
                      font=("Arial", 26, "bold"), foreground=col_data[2]).pack()
            ttk.Separator(stats_frame, orient="vertical").pack(side="left", fill="y", padx=20)

        col3 = ttk.Frame(stats_frame)
        col3.pack(side="left", expand=True)
        ttk.Label(col3, text="Última Descarga", font=("Arial", 9)).pack()
        ttk.Label(col3, textvariable=self.ultima_descarga,
                  font=("Arial", 12, "bold"), foreground="#2980b9").pack()

        # Progress
        prog_frame = ttk.LabelFrame(frame, text="Progreso de la Tarea Actual", padding=10)
        prog_frame.pack(fill="x", pady=(0, 12))

        self.progress_bar = ttk.Progressbar(prog_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 4))

        self.lbl_progress = ttk.Label(prog_frame, text="Sin tarea en ejecución.", foreground="gray")
        self.lbl_progress.pack(anchor="w")

        # Keep-awake
        awake_frame = ttk.LabelFrame(frame, text="Control de Energía del Equipo", padding=10)
        awake_frame.pack(fill="x")

        ttk.Checkbutton(
            awake_frame,
            text="Evitar que el equipo se suspenda o apague mientras el bot está en ejecución",
            variable=self.keep_awake,
            command=self._toggle_keep_awake,
        ).pack(anchor="w")

        self.lbl_awake = ttk.Label(awake_frame, text="Estado: Suspensión permitida.", foreground="gray")
        self.lbl_awake.pack(anchor="w", pady=(4, 0))

    # ── TAB CREDENCIALES ──────────────────────────────────────────────────────
    def _build_tab_credenciales(self, nb):
        frame = ttk.Frame(nb, padding=10)
        nb.add(frame, text="  Credenciales  ")

        # Main creds
        main_frame = ttk.LabelFrame(frame, text="Credenciales Principales", padding=10)
        main_frame.pack(fill="x", pady=(0, 10))

        self._cred_vars_main = {}
        for lbl_text, key, show in [
            ("URL:",           "url",                 ""),
            ("Usuario:",       "usuario",             ""),
            ("Contraseña:",    "contrasena",          "*"),
            ("Verificación:",  "numero_verificacion", ""),
        ]:
            row = ttk.Frame(main_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=lbl_text, width=14, anchor="e").pack(side="left")
            var = tk.StringVar()
            ttk.Entry(row, textvariable=var, show=show, width=50).pack(side="left", padx=6, fill="x", expand=True)
            self._cred_vars_main[key] = var

        ttk.Button(main_frame, text="Guardar Credenciales Principales",
                   command=self._save_main_cred).pack(anchor="e", pady=(8, 0))

        # HC creds
        hc_outer = ttk.LabelFrame(frame, text="Credenciales HC (múltiples usuarios)", padding=10)
        hc_outer.pack(fill="both", expand=True)

        list_row = ttk.Frame(hc_outer)
        list_row.pack(fill="both", expand=True)

        self.hc_listbox = tk.Listbox(list_row, height=5, activestyle="dotbox")
        self.hc_listbox.pack(side="left", fill="both", expand=True)
        self.hc_listbox.bind("<<ListboxSelect>>", self._on_hc_select)

        sb = ttk.Scrollbar(list_row, command=self.hc_listbox.yview)
        sb.pack(side="left", fill="y")
        self.hc_listbox.config(yscrollcommand=sb.set)

        btn_col = ttk.Frame(list_row)
        btn_col.pack(side="left", padx=8, anchor="n")
        ttk.Button(btn_col, text="Nuevo",    command=self._hc_new,          width=12).pack(fill="x", pady=2)
        ttk.Button(btn_col, text="Eliminar", command=self._hc_delete,       width=12).pack(fill="x", pady=2)
        ttk.Button(btn_col, text="Guardar",  command=self._hc_save_selected, width=12).pack(fill="x", pady=2)

        edit_frame = ttk.LabelFrame(hc_outer, text="Editar Credencial Seleccionada", padding=8)
        edit_frame.pack(fill="x", pady=(8, 0))

        self._cred_vars_hc = {}
        for lbl_text, key, show in [
            ("URL:",           "url",                 ""),
            ("Usuario:",       "usuario",             ""),
            ("Contraseña:",    "contrasena",          "*"),
            ("Verificación:",  "numero_verificacion", ""),
        ]:
            row = ttk.Frame(edit_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=lbl_text, width=14, anchor="e").pack(side="left")
            var = tk.StringVar()
            ttk.Entry(row, textvariable=var, show=show, width=45).pack(side="left", padx=6, fill="x", expand=True)
            self._cred_vars_hc[key] = var

    # ── TAB HERRAMIENTAS ──────────────────────────────────────────────────────
    def _build_tab_herramientas(self, nb):
        frame = ttk.Frame(nb, padding=10)
        nb.add(frame, text="  Herramientas  ")

        # Plantilla
        pl_frame = ttk.LabelFrame(frame, text="Plantilla de Carga Masiva", padding=10)
        pl_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(pl_frame, text="Descarga la plantilla CSV para carga masiva de Historias Clínicas.").pack(anchor="w")
        ttk.Button(pl_frame, text="Descargar Plantilla CSV",
                   command=self._download_template).pack(anchor="w", pady=(6, 0))

        # Actualizaciones
        upd_frame = ttk.LabelFrame(frame, text="Actualizaciones", padding=10)
        upd_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(upd_frame, text=f"Versión instalada: v{VERSION_ACTUAL}").pack(anchor="w")
        self.lbl_update_status = ttk.Label(upd_frame, text="", foreground="gray")
        self.lbl_update_status.pack(anchor="w", pady=(2, 6))
        ttk.Button(upd_frame, text="Buscar Nuevas Actualizaciones",
                   command=self._check_updates).pack(anchor="w")

        # Restablecer navegadores
        nav_frame = ttk.LabelFrame(frame, text="Restablecer Navegadores", padding=10)
        nav_frame.pack(fill="x")
        ttk.Label(nav_frame,
                  text="Cierra todos los procesos Chrome / ChromeDriver y elimina archivos\n"
                       "temporales del navegador. Útil cuando el bot queda colgado.").pack(anchor="w")
        ttk.Button(nav_frame, text="Restablecer Navegadores",
                   command=self._reset_browsers).pack(anchor="w", pady=(8, 0))

    # ── TAB LOGS ──────────────────────────────────────────────────────────────
    def _build_tab_logs(self, nb):
        frame = ttk.Frame(nb, padding=10)
        nb.add(frame, text="  Alertas y Logs  ")

        self.txt_logs = scrolledtext.ScrolledText(frame, state="disabled", height=22)
        self.txt_logs.pack(fill="both", expand=True)
        self.txt_logs.tag_config("error",   foreground="red")
        self.txt_logs.tag_config("info",    foreground="blue")
        self.txt_logs.tag_config("success", foreground="green")

        ttk.Button(frame, text="Limpiar Vista", command=self.clear_logs_view).pack(pady=5)

    # ─────────────────────────────────────────────────────────────────────────
    # LÓGICA
    # ─────────────────────────────────────────────────────────────────────────

    def load_config(self):
        try:
            self.config = load_main_config()
            self.maintenance_mode.set(self.config.get("maintenance_mode", False))
            self.update_status_label()
            self._populate_credentials()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar config.json: {e}")

    def _populate_credentials(self):
        cred_main = self.config.get("credenciales", {})
        for key, var in self._cred_vars_main.items():
            var.set(cred_main.get(key, ""))

        self.hc_listbox.delete(0, tk.END)
        for c in self.config.get("credenciales_hc", []):
            self.hc_listbox.insert(tk.END, c.get("usuario", "(sin usuario)"))

    def _save_main_cred(self):
        if "credenciales" not in self.config:
            self.config["credenciales"] = {}
        for key, var in self._cred_vars_main.items():
            self.config["credenciales"][key] = var.get()
        save_main_config(self.config)
        messagebox.showinfo("Guardado", "Credenciales principales guardadas correctamente.")
        self.log_to_view("[SISTEMA] Credenciales principales actualizadas.", "info")

    def _on_hc_select(self, _event=None):
        sel = self.hc_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._selected_hc_index = idx
        hc_list = self.config.get("credenciales_hc", [])
        if idx < len(hc_list):
            cred = hc_list[idx]
            for key, var in self._cred_vars_hc.items():
                var.set(cred.get(key, ""))

    def _hc_new(self):
        new_cred = {"usuario": "NUEVO", "contrasena": "", "numero_verificacion": "", "url": ""}
        if "credenciales_hc" not in self.config:
            self.config["credenciales_hc"] = []
        self.config["credenciales_hc"].append(new_cred)
        save_main_config(self.config)
        self._populate_credentials()
        self.hc_listbox.selection_set(tk.END)
        self._selected_hc_index = len(self.config["credenciales_hc"]) - 1
        for key, var in self._cred_vars_hc.items():
            var.set(new_cred.get(key, ""))

    def _hc_delete(self):
        sel = self.hc_listbox.curselection()
        if not sel:
            messagebox.showwarning("Atención", "Selecciona una credencial para eliminar.")
            return
        idx = sel[0]
        hc_list = self.config.get("credenciales_hc", [])
        if idx < len(hc_list):
            usuario = hc_list[idx].get("usuario", "?")
            if messagebox.askyesno("Confirmar", f"¿Eliminar la credencial de '{usuario}'?"):
                del self.config["credenciales_hc"][idx]
                save_main_config(self.config)
                self._populate_credentials()
                self._selected_hc_index = None
                for var in self._cred_vars_hc.values():
                    var.set("")

    def _hc_save_selected(self):
        if self._selected_hc_index is None:
            messagebox.showwarning("Atención", "Selecciona una credencial de la lista primero.")
            return
        hc_list = self.config.get("credenciales_hc", [])
        if self._selected_hc_index < len(hc_list):
            for key, var in self._cred_vars_hc.items():
                hc_list[self._selected_hc_index][key] = var.get()
            save_main_config(self.config)
            self._populate_credentials()
            messagebox.showinfo("Guardado", "Credencial HC guardada correctamente.")
            self.log_to_view(f"[SISTEMA] Credencial HC [{self._selected_hc_index}] actualizada.", "info")

    def _toggle_keep_awake(self):
        if self.keep_awake.get():
            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            self.lbl_awake.config(
                text="Estado: El equipo NO se apagará ni suspenderá mientras el bot ejecuta.",
                foreground="#27ae60",
            )
            self.log_to_view("[SISTEMA] Suspensión de equipo DESACTIVADA.", "info")
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # ES_CONTINUOUS (clear)
            self.lbl_awake.config(text="Estado: Suspensión permitida.", foreground="gray")
            self.log_to_view("[SISTEMA] Suspensión de equipo REACTIVADA.", "info")

    def _download_template(self):
        if not PLANTILLA_PATH.exists():
            messagebox.showerror("Error", f"No se encontró la plantilla en:\n{PLANTILLA_PATH}")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="PLANTILLA_HC.csv",
            title="Guardar plantilla como...",
        )
        if dest:
            shutil.copy2(str(PLANTILLA_PATH), dest)
            messagebox.showinfo("Listo", f"Plantilla guardada en:\n{dest}")
            self.log_to_view(f"[SISTEMA] Plantilla descargada a: {dest}", "info")

    def _check_updates(self):
        self.lbl_update_status.config(text="Verificando, espera...", foreground="gray")

        def do_check():
            try:
                import urllib.request
                import json as _json
                with urllib.request.urlopen(UPDATE_CHECK_URL, timeout=8) as resp:
                    data = _json.loads(resp.read().decode())
                latest = data.get("tag_name", "").lstrip("v")
                if latest and latest != VERSION_ACTUAL:
                    self.root.after(0, lambda: self.lbl_update_status.config(
                        text=f"Nueva versión disponible: v{latest}", foreground="#e67e22"))
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Actualización disponible",
                        f"Nueva versión: v{latest}\nVersión actual: v{VERSION_ACTUAL}\n\n"
                        "Visita GitHub para descargar la nueva versión.",
                    ))
                else:
                    self.root.after(0, lambda: self.lbl_update_status.config(
                        text=f"Tienes la versión más reciente (v{VERSION_ACTUAL}).",
                        foreground="#27ae60",
                    ))
            except Exception as ex:
                self.root.after(0, lambda: self.lbl_update_status.config(
                    text=f"Error al verificar: {ex}", foreground="red"))

        threading.Thread(target=do_check, daemon=True).start()

    def _reset_browsers(self):
        if not messagebox.askyesno(
            "Confirmar",
            "¿Cerrar todos los procesos Chrome y ChromeDriver?\n"
            "Esto detendrá cualquier descarga en curso.",
        ):
            return
        killed = 0
        for proc_name in ("chrome.exe", "chromedriver.exe"):
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", proc_name],
                    capture_output=True, text=True,
                )
                if result.returncode == 0:
                    killed += 1
            except Exception:
                pass
        # Clean temp chromedriver scoped dirs
        temp = os.environ.get("TEMP", "")
        cleaned = 0
        if temp:
            for item in Path(temp).glob("scoped_dir*"):
                try:
                    shutil.rmtree(item, ignore_errors=True)
                    cleaned += 1
                except Exception:
                    pass
        msg = f"Procesos cerrados: {killed}/2.\nCarpetas temporales eliminadas: {cleaned}."
        messagebox.showinfo("Navegadores restablecidos", msg)
        self.log_to_view(f"[SISTEMA] Navegadores restablecidos. {msg}", "info")

    # ── MANTENIMIENTO / MONITOREO ─────────────────────────────────────────────
    def save_config(self):
        try:
            save_main_config(self.config)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar config.json: {e}")

    def update_status_label(self):
        if self.maintenance_mode.get():
            self.lbl_status.config(text="EN MANTENIMIENTO — Usuarios Bloqueados", foreground="red")
        else:
            self.lbl_status.config(text="OPERATIVO", foreground="#27ae60")

    def toggle_maintenance(self):
        new_state = not self.maintenance_mode.get()
        self.maintenance_mode.set(new_state)
        self.config["maintenance_mode"] = new_state
        self.save_config()
        self.update_status_label()
        state_str = "ACTIVADO" if new_state else "DESACTIVADO"
        self.log_to_view(f"[SISTEMA] Modo Mantenimiento {state_str}", "info")

    # Público: llamado desde el bot para actualizar progreso en el dashboard
    def update_progress(self, current: int, total: int, label: str = ""):
        if total > 0:
            self.progress_bar["maximum"] = total
            self.progress_bar["value"] = current
        self.lbl_progress.config(text=label or f"{current} / {total}")
        self.total_descargados.set(current)
        self.total_pendientes.set(max(0, total - current))
        if current > 0:
            self.ultima_descarga.set(time.strftime("%d/%m/%Y %H:%M"))

    def monitor_alerts(self):
        if not os.path.exists(ALERTS_LOG_PATH):
            open(ALERTS_LOG_PATH, "w").close()

        while True:
            try:
                if os.path.exists(ALERTS_LOG_PATH):
                    current_size = os.path.getsize(ALERTS_LOG_PATH)
                    if current_size > self.last_log_size:
                        with open(ALERTS_LOG_PATH, "r", encoding="utf-8") as f:
                            f.seek(self.last_log_size)
                            new_lines = f.readlines()
                            self.last_log_size = f.tell()
                            for line in new_lines:
                                if line.strip():
                                    try:
                                        data = json.loads(line)
                                        self.process_alert(data)
                                    except Exception:
                                        pass
            except Exception as e:
                print(f"Error monitor: {e}")
            time.sleep(2)

    def process_alert(self, data):
        timestamp = data.get("timestamp", "?")
        user = data.get("user", "Desconocido")
        uid = data.get("user_id", "")
        event_type = data.get("type", "ERROR")

        # Auto-update HC download counter
        if event_type == "SUCCESS" and "hc" in str(data.get("message", "")).lower():
            new_val = self.total_descargados.get() + 1
            self.root.after(0, lambda v=new_val: self.total_descargados.set(v))
            now = time.strftime("%d/%m/%Y %H:%M")
            self.root.after(0, lambda t=now: self.ultima_descarga.set(t))

        if event_type == "SUCCESS":
            msg_text = data.get("message", "Acción completada")
            details = data.get("details", "")
            display_text = (
                f"[{timestamp}] ACTIVIDAD — Usuario: {user} (ID: {uid})\n"
                f"Acción: {msg_text}\n"
                f"Detalles: {details}"
            )
            tag = "success"
        else:
            error = data.get("message") or data.get("error", "Error desconocido")
            display_text = (
                f"[{timestamp}] ERROR — Usuario: {user} (ID: {uid})\n"
                f"Fallo: {error}\n"
            )
            tag = "error"

        self.root.after(0, lambda t=display_text, tg=tag: self.log_to_view(t, tg))

    def log_to_view(self, text, tag=None):
        self.txt_logs.config(state="normal")
        self.txt_logs.insert(tk.END, text + "\n" + "─" * 50 + "\n", tag)
        self.txt_logs.see(tk.END)
        self.txt_logs.config(state="disabled")

    def clear_logs_view(self):
        self.txt_logs.config(state="normal")
        self.txt_logs.delete("1.0", tk.END)
        self.txt_logs.config(state="disabled")

    def on_closing(self):
        if self.keep_awake.get():
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AdminPanelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
