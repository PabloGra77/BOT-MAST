# -*- coding: utf-8 -*-
"""
BOT360 - Aplicacion Desktop Principal
Panel de control con gestion de credenciales y navegadores
"""
from __future__ import annotations
import sys
import json
import os
import threading
import subprocess
from pathlib import Path
from typing import Optional, List

# ---------------------------------------------------------------------------
# Asegurar que src/ este en el path
# ---------------------------------------------------------------------------
_SRC_DIR = Path(__file__).resolve().parent.parent   # src/
_ROOT_DIR = _SRC_DIR.parent                          # BOT360/
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
        QTextEdit, QTableWidget, QTableWidgetItem, QMessageBox, QDialog,
        QFormLayout, QDialogButtonBox, QCheckBox, QGroupBox, QFrame,
        QSizePolicy, QSlider, QHeaderView, QAbstractItemView,
        QListWidget, QListWidgetItem, QStatusBar, QFileDialog, QProgressBar
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QDateTime, QSize
    from PyQt6.QtGui import QFont, QTextCursor
except ImportError:
    print("ERROR: PyQt6 no instalado. Ejecuta: pip install PyQt6")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
_CONFIG_PATH = _ROOT_DIR / "config" / "config.json"

def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_config(cfg: dict):
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

try:
    from bot360_app.common.settings import CONFIG_PATH as _SP
    def load_main_config() -> dict:
        return _load_config()
    def save_main_config(cfg: dict):
        _save_config(cfg)
except ImportError:
    load_main_config = _load_config
    save_main_config = _save_config

VERSION = "9.3.1"
MAX_BROWSERS = 5

# ===========================================================================
# Estilos
# ===========================================================================
DARK_STYLE = """
QMainWindow, QDialog {background-color: #1a1a2e; color: #e0e0e0;}
QWidget {background-color: #1a1a2e; color: #e0e0e0; font-size: 13px;}
QTabWidget::pane {border: 1px solid #0f3460; background: #16213e;}
QTabBar::tab {background: #16213e; color: #a0a0b0; padding: 8px 18px; border: 1px solid #0f3460;}
QTabBar::tab:selected {background: #0f3460; color: #e94560; font-weight: bold;}
QTabBar::tab:hover {background: #0f3460; color: #ffffff;}
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #0f3460, stop:1 #0a2444);
    color: #ffffff; border: 1px solid #e94560; border-radius: 5px;
    padding: 6px 14px; font-weight: bold;}
QPushButton:hover {background: #e94560; color: #ffffff;}
QPushButton:pressed {background: #c73652;}
QPushButton:disabled {background: #333355; color: #666688; border-color: #444466;}
QPushButton[class="danger"] {background: #6b1a2a; border-color: #cc2244;}
QPushButton[class="danger"]:hover {background: #cc2244;}
QPushButton[class="success"] {background: #1a4a2a; border-color: #22cc44;}
QPushButton[class="success"]:hover {background: #22cc44; color: #000;}
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background: #16213e; color: #e0e0e0; border: 1px solid #0f3460;
    border-radius: 4px; padding: 5px;}
QLineEdit:focus, QComboBox:focus {border-color: #e94560;}
QGroupBox {border: 1px solid #0f3460; margin-top: 10px; padding-top: 8px;
    font-weight: bold; color: #e94560;}
QGroupBox::title {subcontrol-origin: margin; left: 8px; top: -2px; padding: 0 4px;}
QTableWidget {background: #16213e; color: #e0e0e0; gridline-color: #0f3460;
    selection-background-color: #e94560; selection-color: #fff;}
QHeaderView::section {background: #0f3460; color: #e0e0e0; padding: 6px; border: 1px solid #1a2a50;}
QScrollBar:vertical {background: #16213e; width: 10px;}
QScrollBar::handle:vertical {background: #0f3460; border-radius: 5px;}
QCheckBox::indicator {width: 16px; height: 16px; border: 1px solid #0f3460; background: #16213e;}
QCheckBox::indicator:checked {background: #e94560; border-color: #e94560;}
QSlider::groove:horizontal {background: #16213e; height: 6px; border-radius: 3px;}
QSlider::handle:horizontal {background: #e94560; width: 14px; height: 14px;
    margin: -4px 0; border-radius: 7px;}
QSlider::sub-page:horizontal {background: #0f3460; border-radius: 3px;}
QStatusBar {background: #0f3460; color: #a0a0b0; border-top: 1px solid #e94560;}
"""


# ===========================================================================
# Tab: Credenciales
# ===========================================================================
class CredencialesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hc_data: List[dict] = []
        self._build_ui()
        self.load_from_config()

    def _build_ui(self):
        main = QVBoxLayout(self)

        # Credencial Principal
        grp_main = QGroupBox("Credencial Principal  (para Agendas)")
        main.addWidget(grp_main)
        vl = QVBoxLayout(grp_main)

        form = QFormLayout()
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Usuario del sistema (ej: PGRANADOS)")
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("Contrasena")
        self.txt_verif = QLineEdit()
        self.txt_verif.setPlaceholderText("Numero de verificacion (ej: Inpec)")
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("URL del portal")

        # fila pass con toggle
        rp = QHBoxLayout()
        rp.addWidget(self.txt_pass)
        btn_tp = QPushButton("Mostrar")
        btn_tp.setFixedWidth(72)
        btn_tp.clicked.connect(lambda: self._toggle(self.txt_pass, btn_tp))
        rp.addWidget(btn_tp)
        wp = QWidget(); wp.setLayout(rp)

        form.addRow("Usuario:", self.txt_user)
        form.addRow("Contrasena:", wp)
        form.addRow("Verificacion:", self.txt_verif)
        form.addRow("URL:", self.txt_url)
        vl.addLayout(form)

        rb = QHBoxLayout()
        btn_g = QPushButton("Guardar Credencial Principal")
        btn_g.setProperty("class", "success")
        btn_g.clicked.connect(self.save_main_cred)
        btn_p = QPushButton("Probar URL")
        btn_p.clicked.connect(self._probar_url)
        rb.addWidget(btn_g)
        rb.addWidget(btn_p)
        vl.addLayout(rb)

        # Credenciales HC
        grp_hc = QGroupBox("Credenciales HC  (una por navegador adicional)")
        main.addWidget(grp_hc)
        vl2 = QVBoxLayout(grp_hc)

        lbl_info = QLabel("Agrega credenciales adicionales para ejecutar descargas HC en paralelo.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color:#8888cc; font-size:11px;")
        vl2.addWidget(lbl_info)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Usuario", "Contrasena", "Verificacion", "URL"])
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setMaximumHeight(160)
        vl2.addWidget(self.tbl)

        rb2 = QHBoxLayout()
        for lbl_btn, slot, cls in [
            ("Agregar HC", self._add, ""),
            ("Editar", self._edit, ""),
            ("Eliminar", self._del, "danger"),
            ("Guardar HCs", self._save_hc, "success"),
        ]:
            b = QPushButton(lbl_btn)
            if cls:
                b.setProperty("class", cls)
            b.clicked.connect(slot)
            rb2.addWidget(b)
        vl2.addLayout(rb2)

        self.lbl_st = QLabel("")
        self.lbl_st.setStyleSheet("color:#22cc44; font-size:11px;")
        main.addWidget(self.lbl_st)
        main.addStretch()

    # helpers
    def _toggle(self, field, btn):
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("Ocultar")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("Mostrar")

    def _refresh_table(self):
        self.tbl.setRowCount(0)
        for r, c in enumerate(self._hc_data):
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(c.get("usuario", "")))
            masked = "*" * len(c.get("contrasena", ""))
            self.tbl.setItem(r, 1, QTableWidgetItem(masked))
            self.tbl.setItem(r, 2, QTableWidgetItem(c.get("numero_verificacion", "")))
            self.tbl.setItem(r, 3, QTableWidgetItem(c.get("url", "")))

    def _status(self, msg, color="#22cc44"):
        self.lbl_st.setText(msg)
        self.lbl_st.setStyleSheet(f"color:{color}; font-size:11px;")

    # acciones
    def load_from_config(self):
        cfg = load_main_config()
        c = cfg.get("credenciales", {})
        self.txt_user.setText(c.get("usuario", ""))
        self.txt_pass.setText(c.get("contrasena", ""))
        self.txt_verif.setText(c.get("numero_verificacion", ""))
        self.txt_url.setText(c.get("url", ""))
        self._hc_data = list(cfg.get("credenciales_hc", []))
        self._refresh_table()

    def save_main_cred(self):
        if not self.txt_user.text().strip():
            QMessageBox.warning(self, "Error", "El usuario no puede estar vacio.")
            return
        cfg = load_main_config()
        cfg["credenciales"] = {
            "usuario": self.txt_user.text().strip().upper(),
            "contrasena": self.txt_pass.text(),
            "numero_verificacion": self.txt_verif.text().strip(),
            "url": self.txt_url.text().strip(),
        }
        save_main_config(cfg)
        self._status("Credencial principal guardada")

    def _save_hc(self):
        cfg = load_main_config()
        cfg["credenciales_hc"] = self._hc_data
        save_main_config(cfg)
        self._status(f"{len(self._hc_data)} credencial(es) HC guardadas")

    def _add(self):
        if len(self._hc_data) >= MAX_BROWSERS:
            QMessageBox.warning(self, "Limite", f"Maximo {MAX_BROWSERS} credenciales HC.")
            return
        dlg = _CredDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if d["usuario"]:
                self._hc_data.append(d)
                self._refresh_table()
                self._status("HC agregada — recuerda guardar", "#ffaa00")

    def _edit(self):
        r = self.tbl.currentRow()
        if r < 0:
            QMessageBox.information(self, "Info", "Selecciona una fila.")
            return
        dlg = _CredDialog(self, self._hc_data[r])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._hc_data[r] = dlg.get_data()
            self._refresh_table()
            self._status("HC modificada — recuerda guardar", "#ffaa00")

    def _del(self):
        r = self.tbl.currentRow()
        if r < 0:
            return
        u = self._hc_data[r].get("usuario", "")
        if QMessageBox.question(self, "Eliminar", f"Eliminar '{u}'?") == QMessageBox.StandardButton.Yes:
            self._hc_data.pop(r)
            self._refresh_table()
            self._status("HC eliminada — recuerda guardar", "#ffaa00")

    def _probar_url(self):
        import webbrowser
        url = self.txt_url.text().strip()
        if url:
            webbrowser.open(url)
        else:
            QMessageBox.warning(self, "Error", "Ingresa una URL primero.")


class _CredDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Credencial HC")
        self.setMinimumWidth(420)
        self.setStyleSheet(DARK_STYLE)
        d = data or {}
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.txt_u = QLineEdit(d.get("usuario", ""))
        self.txt_p = QLineEdit(d.get("contrasena", ""))
        self.txt_p.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_v = QLineEdit(d.get("numero_verificacion", ""))
        self.txt_url = QLineEdit(d.get("url", "https://sisipec.salud360.app/Inpec360/servlet/ingreso"))
        form.addRow("Usuario:", self.txt_u)
        form.addRow("Contrasena:", self.txt_p)
        form.addRow("Verificacion:", self.txt_v)
        form.addRow("URL:", self.txt_url)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self):
        return {
            "usuario": self.txt_u.text().strip().upper(),
            "contrasena": self.txt_p.text(),
            "numero_verificacion": self.txt_v.text().strip(),
            "url": self.txt_url.text().strip(),
        }


# ===========================================================================
# Tab: Navegadores
# ===========================================================================
class NavegadoresTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load_from_config()

    def _build_ui(self):
        main = QVBoxLayout(self)

        grp_tipo = QGroupBox("Tipo de Navegador")
        main.addWidget(grp_tipo)
        fl = QFormLayout(grp_tipo)
        self.cmb = QComboBox()
        self.cmb.addItems(["chrome", "edge"])
        self.cmb.setToolTip("Selecciona el navegador instalado en este equipo")
        fl.addRow("Navegador:", self.cmb)
        self.chk_headless = QCheckBox("Modo silencioso (sin ventana visible)")
        self.chk_headless.setToolTip("Headless: el bot trabaja sin mostrar el navegador. Mas rapido.")
        fl.addRow("", self.chk_headless)

        grp_cant = QGroupBox(f"Cantidad de Navegadores Paralelos  (max {MAX_BROWSERS})")
        main.addWidget(grp_cant)
        vl2 = QVBoxLayout(grp_cant)

        lbl_info = QLabel(
            "Cada navegador ejecuta una sesion independiente.\n"
            "Mas navegadores = mayor paralelismo pero mas uso de CPU/RAM."
        )
        lbl_info.setStyleSheet("color:#8888cc; font-size:11px;")
        vl2.addWidget(lbl_info)

        row_sl = QHBoxLayout()
        self.sld = QSlider(Qt.Orientation.Horizontal)
        self.sld.setMinimum(1)
        self.sld.setMaximum(MAX_BROWSERS)
        self.sld.setValue(1)
        self.sld.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sld.setTickInterval(1)
        self.sld.valueChanged.connect(self._on_slide)
        self.lbl_n = QLabel("1")
        self.lbl_n.setStyleSheet("color:#e94560; font-size:26px; font-weight:bold;")
        self.lbl_n.setFixedWidth(36)
        self.lbl_n.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row_sl.addWidget(self.sld)
        row_sl.addWidget(self.lbl_n)
        vl2.addLayout(row_sl)

        # iconos visuales
        self.icons_row = QHBoxLayout()
        self._icons: List[QLabel] = []
        for _ in range(MAX_BROWSERS):
            ico = QLabel("O")
            ico.setFixedSize(QSize(44, 44))
            ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico.setStyleSheet("font-size:22px; background:#16213e; border-radius:8px; border:1px solid #333355;")
            self._icons.append(ico)
            self.icons_row.addWidget(ico)
        self.icons_row.addStretch()
        vl2.addLayout(self.icons_row)

        self.lbl_req = QLabel("")
        self.lbl_req.setStyleSheet("color:#8888cc; font-size:11px; font-style:italic;")
        self.lbl_req.setWordWrap(True)
        vl2.addWidget(self.lbl_req)

        grp_adv = QGroupBox("Opciones Avanzadas")
        main.addWidget(grp_adv)
        fl2 = QFormLayout(grp_adv)
        self.spn_timeout = QSpinBox()
        self.spn_timeout.setMinimum(10)
        self.spn_timeout.setMaximum(120)
        self.spn_timeout.setValue(30)
        self.spn_timeout.setSuffix(" seg")
        fl2.addRow("Timeout elementos:", self.spn_timeout)

        self.txt_dl = QLineEdit()
        self.txt_dl.setReadOnly(True)
        self.txt_dl.setPlaceholderText("Dejar vacio para usar carpeta predeterminada")
        btn_br = QPushButton("...")
        btn_br.setFixedWidth(32)
        btn_br.clicked.connect(self._browse)
        row_dl = QHBoxLayout()
        row_dl.addWidget(self.txt_dl)
        row_dl.addWidget(btn_br)
        w_dl = QWidget(); w_dl.setLayout(row_dl)
        fl2.addRow("Carpeta descargas:", w_dl)

        grp_check = QGroupBox("Estado de Navegadores Instalados")
        main.addWidget(grp_check)
        vl3 = QVBoxLayout(grp_check)
        r_st = QHBoxLayout()
        self.lbl_ch = QLabel("Chrome: --")
        self.lbl_ed = QLabel("Edge: --")
        r_st.addWidget(self.lbl_ch)
        r_st.addWidget(self.lbl_ed)
        vl3.addLayout(r_st)
        btn_verify = QPushButton("Verificar Navegadores Instalados")
        btn_verify.clicked.connect(self.check_browsers)
        vl3.addWidget(btn_verify)

        row_save = QHBoxLayout()
        row_save.addStretch()
        btn_save = QPushButton("Guardar Configuracion de Navegadores")
        btn_save.setProperty("class", "success")
        btn_save.clicked.connect(self.save_config)
        row_save.addWidget(btn_save)
        main.addLayout(row_save)

        self.lbl_st = QLabel("")
        self.lbl_st.setStyleSheet("color:#22cc44; font-size:11px;")
        main.addWidget(self.lbl_st)
        main.addStretch()

        # init icons
        self._on_slide(1)

    def _on_slide(self, v):
        self.lbl_n.setText(str(v))
        for i, ico in enumerate(self._icons):
            if i < v:
                ico.setStyleSheet(
                    "font-size:22px; background:#0f3460; border-radius:8px; "
                    "border:2px solid #e94560; color:#e0e0e0;"
                )
            else:
                ico.setStyleSheet(
                    "font-size:22px; background:#16213e; border-radius:8px; "
                    "border:1px solid #333355; color:#444;"
                )
        if v == 1:
            self.lbl_req.setText("Con 1 navegador solo se necesita la credencial principal.")
        else:
            self.lbl_req.setText(
                f"Con {v} navegadores se usan credenciales HC ({v} credenciales en total). "
                "Configuralas en la pestana Credenciales."
            )

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta de descargas")
        if d:
            self.txt_dl.setText(d)

    def load_from_config(self):
        cfg = load_main_config()
        nav = cfg.get("navegadores", {})
        idx = self.cmb.findText(nav.get("tipo", "chrome"))
        self.cmb.setCurrentIndex(max(0, idx))
        cantidad = max(1, min(MAX_BROWSERS, int(nav.get("cantidad_max", 1))))
        self.sld.setValue(cantidad)
        self.chk_headless.setChecked(bool(nav.get("headless", False)))
        self.spn_timeout.setValue(int(nav.get("timeout", 30)))
        self.txt_dl.setText(nav.get("carpeta_descargas", ""))
        self._on_slide(cantidad)

    def save_config(self):
        cfg = load_main_config()
        cfg["navegadores"] = {
            "tipo": self.cmb.currentText(),
            "cantidad_max": self.sld.value(),
            "headless": self.chk_headless.isChecked(),
            "timeout": self.spn_timeout.value(),
            "carpeta_descargas": self.txt_dl.text().strip(),
        }
        save_main_config(cfg)
        self.lbl_st.setText(
            f"Guardado: {self.sld.value()} navegador(es) [{self.cmb.currentText()}]"
        )

    def check_browsers(self):
        import shutil
        def _ok(paths):
            return any(Path(p).exists() for p in paths)

        ch = _ok([
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ])
        ed = _ok([
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ])
        self.lbl_ch.setText(f"Chrome: {'Instalado' if ch else 'No encontrado'}")
        self.lbl_ed.setText(f"Edge: {'Instalado' if ed else 'No encontrado'}")
        if not ch and not ed:
            QMessageBox.warning(
                self, "Sin navegadores",
                "No se detecto Chrome ni Edge en este equipo.\n"
                "Instala al menos uno para usar el bot.\n\n"
                "Chrome: https://www.google.com/chrome/\n"
                "Edge: https://www.microsoft.com/es-es/edge"
            )


# ===========================================================================
# Tab: Dashboard
# ===========================================================================
class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        hdr = QLabel("BOT360  |  Panel de Control")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet("color:#e94560; font-size:22px; font-weight:bold; margin-bottom:4px;")
        lay.addWidget(hdr)

        sub = QLabel("Automatizacion de Agendas y Gestion de Historias Clinicas")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#8888cc; font-size:13px; margin-bottom:12px;")
        lay.addWidget(sub)

        cards = QHBoxLayout()
        for titulo, val, col in [
            ("Version", VERSION, "#e94560"),
            ("Estado",  "Listo", "#22cc44"),
            ("Navegadores", "0 activos", "#e9a020"),
        ]:
            fr = QFrame()
            fr.setStyleSheet(f"background:#16213e; border:1px solid {col}; border-radius:8px; padding:4px;")
            cv = QVBoxLayout(fr)
            lv = QLabel(val)
            lv.setStyleSheet(f"color:{col}; font-size:20px; font-weight:bold;")
            lv.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lt = QLabel(titulo)
            lt.setStyleSheet("color:#a0a0b0; font-size:11px;")
            lt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lv); cv.addWidget(lt)
            cards.addWidget(fr)
        lay.addLayout(cards)

        grp = QGroupBox("Actividad Reciente")
        lay.addWidget(grp)
        gl = QVBoxLayout(grp)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(130)
        self.log_box.setStyleSheet(
            "background:#0a1020; color:#22cc44; font-family:Consolas,monospace; font-size:11px;"
        )
        gl.addWidget(self.log_box)

        self._log("Sistema iniciado")
        lay.addStretch()

    def _log(self, msg):
        ts = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.log_box.append(f"[{ts}] {msg}")
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)


# ===========================================================================
# Tab: Crear Agenda
# ===========================================================================
class AgendaTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        grp = QGroupBox("Parametros de Agenda")
        lay.addWidget(grp)
        form = QFormLayout(grp)
        self.cmb_sede = QComboBox()
        self.cmb_sede.addItem("-- Seleccionar sede --")
        cfg = load_main_config()
        self.cmb_sede.addItems(sorted(cfg.get("sedes", [])))
        form.addRow("Sede:", self.cmb_sede)
        self.txt_apellido = QLineEdit()
        self.txt_apellido.setPlaceholderText("Primer apellido del profesional")
        form.addRow("Apellido:", self.txt_apellido)
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Primer nombre del profesional")
        form.addRow("Nombre:", self.txt_nombre)
        self.txt_fi = QLineEdit(); self.txt_fi.setPlaceholderText("DD/MM/YYYY")
        self.txt_ff = QLineEdit(); self.txt_ff.setPlaceholderText("DD/MM/YYYY")
        form.addRow("Fecha inicio:", self.txt_fi)
        form.addRow("Fecha fin:", self.txt_ff)
        rb = QHBoxLayout()
        btn = QPushButton("Iniciar Creacion de Agenda")
        btn.setProperty("class", "success")
        btn.clicked.connect(self._run)
        rb.addWidget(btn)
        lay.addLayout(rb)
        lay.addWidget(QLabel("Log:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background:#0a1020; color:#22cc44; font-family:Consolas,monospace; font-size:11px;")
        lay.addWidget(self.log)

    def _run(self):
        if not self.txt_apellido.text().strip():
            QMessageBox.warning(self, "Error", "Ingresa el apellido del profesional.")
            return
        self.log.append("[INFO] Iniciando creacion de agenda...")
        self.log.append(f"      Profesional: {self.txt_apellido.text()} {self.txt_nombre.text()}")
        self.log.append("[NOTA] Conectar con bot_engine.Bot para ejecucion real.")


# ===========================================================================
# Tab: Historia Clinica
# ===========================================================================
class HCTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ids: List[str] = []
        self._rows: List[dict] = []   # filas completas con fechas por paciente
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        # ── Fechas compartidas ───────────────────────────────────────────
        grp_fecha = QGroupBox("Rango de Fechas (global — opcional si el Excel ya trae fechas por paciente)")
        lay.addWidget(grp_fecha)
        flay = QHBoxLayout(grp_fecha)
        flay.addWidget(QLabel("Fecha inicio:"))
        self.txt_fi = QLineEdit(); self.txt_fi.setPlaceholderText("DD/MM/YYYY"); self.txt_fi.setMaximumWidth(130)
        flay.addWidget(self.txt_fi)
        flay.addWidget(QLabel("Fecha fin:"))
        self.txt_ff = QLineEdit(); self.txt_ff.setPlaceholderText("DD/MM/YYYY"); self.txt_ff.setMaximumWidth(130)
        flay.addWidget(self.txt_ff)
        flay.addStretch()

        # ── Tabs: Individual / Masiva ────────────────────────────────────
        inner_tabs = QTabWidget()
        lay.addWidget(inner_tabs)

        # — Tab Individual —
        w_ind = QWidget()
        inner_tabs.addTab(w_ind, "Individual")
        vind = QVBoxLayout(w_ind)
        form = QFormLayout()
        self.txt_id = QLineEdit(); self.txt_id.setPlaceholderText("ID del paciente")
        form.addRow("ID Paciente:", self.txt_id)
        vind.addLayout(form)
        rb_ind = QHBoxLayout()
        btn_ind = QPushButton("Descargar HC")
        btn_ind.setProperty("class", "success")
        btn_ind.clicked.connect(self._run_individual)
        rb_ind.addWidget(btn_ind)
        btn_open = QPushButton("Abrir Carpeta")
        btn_open.clicked.connect(self._open)
        rb_ind.addWidget(btn_open)
        vind.addLayout(rb_ind)
        vind.addStretch()

        # — Tab Masiva —
        w_mas = QWidget()
        inner_tabs.addTab(w_mas, "Descarga Masiva")
        vmas = QVBoxLayout(w_mas)

        # Cargar archivo
        hf = QHBoxLayout()
        self.txt_archivo = QLineEdit(); self.txt_archivo.setPlaceholderText("Selecciona archivo Excel (.xlsx) o CSV con columna 'id' o 'documento'")
        self.txt_archivo.setReadOnly(True)
        btn_browse = QPushButton("Examinar...")
        btn_browse.setMaximumWidth(100)
        btn_browse.clicked.connect(self._browse_file)
        hf.addWidget(self.txt_archivo); hf.addWidget(btn_browse)
        vmas.addLayout(hf)

        # Tabla de IDs
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["#", "ID / Documento", "Fecha Inicio", "Fecha Fin", "Estado"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 40)
        self.tabla.setColumnWidth(1, 150)
        self.tabla.setColumnWidth(2, 100)
        self.tabla.setColumnWidth(3, 100)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        vmas.addWidget(self.tabla)

        # Contador
        self.lbl_conteo = QLabel("0 pacientes cargados")
        self.lbl_conteo.setStyleSheet("color:#aaaaaa; font-size:11px;")
        vmas.addWidget(self.lbl_conteo)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v / %m pacientes")
        vmas.addWidget(self.progress)

        # Botones masiva
        rb_mas = QHBoxLayout()
        btn_masiva = QPushButton("Iniciar Descarga Masiva")
        btn_masiva.setProperty("class", "success")
        btn_masiva.clicked.connect(self._run_masiva)
        btn_limpiar = QPushButton("Limpiar Lista")
        btn_limpiar.clicked.connect(self._limpiar)
        btn_open2 = QPushButton("Abrir Carpeta")
        btn_open2.clicked.connect(self._open)
        rb_mas.addWidget(btn_masiva); rb_mas.addWidget(btn_limpiar); rb_mas.addWidget(btn_open2)
        vmas.addLayout(rb_mas)

        # Log
        lay.addWidget(QLabel("Log:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background:#0a1020; color:#22cc44; font-family:Consolas,monospace; font-size:11px;")
        self.log.setMaximumHeight(130)
        lay.addWidget(self.log)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de pacientes",
            str(Path.home()),
            "Archivos de datos (*.xlsx *.xls *.csv);;Todos (*.*)"
        )
        if not path:
            return
        self.txt_archivo.setText(path)
        self._cargar_ids(path)

    def _cargar_ids(self, path: str):
        self._ids = []
        self._rows = []
        self.tabla.setRowCount(0)
        try:
            p = Path(path)
            if p.suffix.lower() in (".xlsx", ".xls"):
                try:
                    import pandas as pd
                    df = pd.read_excel(path, dtype=str)
                except Exception:
                    self.log.append("[ERROR] No se pudo leer el Excel. Verifica que pandas y openpyxl esten instalados.")
                    return
            else:
                try:
                    import pandas as pd
                    df = pd.read_csv(path, dtype=str, encoding="utf-8")
                except Exception:
                    try:
                        import pandas as pd
                        df = pd.read_csv(path, dtype=str, encoding="latin-1")
                    except Exception:
                        self.log.append("[ERROR] No se pudo leer el CSV.")
                        return

            # Normalizar nombres de columnas para búsqueda insensible
            col_map = {c.strip().upper(): c for c in df.columns}

            # Buscar columna con IDs
            col = None
            for c in df.columns:
                if c.strip().lower() in ("cc", "id", "documento", "cedula", "nro_documento", "id_paciente", "paciente"):
                    col = c
                    break
            if col is None:
                col = df.columns[0]
                self.log.append(f"[AVISO] Columna 'id' no encontrada, usando primera columna: '{col}'")

            # Buscar columnas opcionales del Excel
            def _find_col(*names):
                for n in names:
                    if n.upper() in col_map:
                        return col_map[n.upper()]
                return None

            col_fi   = _find_col("FECHA INICIO", "FECHA_INICIO", "F_INICIO", "DESDE")
            col_ff   = _find_col("FECHA FIN", "FECHA_FIN", "F_FIN", "HASTA")
            col_srv  = _find_col("SERVICIO")
            col_est  = _find_col("ESTRATEGIA")
            col_fac  = _find_col("NUMERO DE FACTURA", "NUMERO_FACTURA", "FACTURA", "NRO_FACTURA")

            tiene_fechas = bool(col_fi and col_ff)
            if tiene_fechas:
                self.log.append(f"[OK] Columnas FECHA INICIO / FECHA FIN detectadas — se usarán fechas del Excel")
            else:
                self.log.append(f"[INFO] El Excel no tiene columnas de fecha — ingresa el rango global arriba")

            # Construir lista de filas (sin duplicar IDs, preservar primera ocurrencia)
            seen = set()
            rows = []
            for _, row in df.iterrows():
                id_val = str(row[col]).strip() if row[col] == row[col] else ""
                if not id_val or id_val.lower() in ("nan", "none", "") or id_val in seen:
                    continue
                seen.add(id_val)
                rows.append({
                    "id":           id_val,
                    "fecha_inicio": str(row[col_fi]).strip()  if col_fi  and row[col_fi]  == row[col_fi]  else "",
                    "fecha_fin":    str(row[col_ff]).strip()  if col_ff  and row[col_ff]  == row[col_ff]  else "",
                    "servicio":     str(row[col_srv]).strip() if col_srv and row[col_srv] == row[col_srv] else "",
                    "estrategia":   str(row[col_est]).strip() if col_est and row[col_est] == row[col_est] else "",
                    "factura":      str(row[col_fac]).strip() if col_fac and row[col_fac] == row[col_fac] else "",
                })

            self._rows = rows
            self._ids  = [r["id"] for r in rows]

            self.tabla.setRowCount(len(rows))
            for i, r in enumerate(rows):
                self.tabla.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.tabla.setItem(i, 1, QTableWidgetItem(r["id"]))
                self.tabla.setItem(i, 2, QTableWidgetItem(r["fecha_inicio"] or "—"))
                self.tabla.setItem(i, 3, QTableWidgetItem(r["fecha_fin"]    or "—"))
                self.tabla.setItem(i, 4, QTableWidgetItem("Pendiente"))

            self.progress.setMaximum(len(rows))
            self.progress.setValue(0)
            self.lbl_conteo.setText(f"{len(rows)} pacientes cargados desde '{Path(path).name}'")
            self.log.append(f"[OK] {len(rows)} IDs cargados desde {Path(path).name}")

        except Exception as e:
            self.log.append(f"[ERROR] {e}")

    def _limpiar(self):
        self._ids = []
        self._rows = []
        self.tabla.setRowCount(0)
        self.txt_archivo.clear()
        self.progress.setValue(0)
        self.lbl_conteo.setText("0 pacientes cargados")
        self.log.append("[INFO] Lista limpiada.")

    def _run_individual(self):
        if not self.txt_id.text().strip():
            QMessageBox.warning(self, "Error", "Ingresa el ID del paciente.")
            return
        fi = self.txt_fi.text().strip()
        ff = self.txt_ff.text().strip()
        self.log.append(f"[INFO] Descargando HC paciente {self.txt_id.text()} | {fi} → {ff}")
        self.log.append("[NOTA] Conectar con bot_engine.Bot para ejecucion real.")

    def _run_masiva(self):
        if not self._rows:
            QMessageBox.warning(self, "Sin datos", "Primero carga un archivo con IDs de pacientes.")
            return

        fi_global = self.txt_fi.text().strip()
        ff_global = self.txt_ff.text().strip()

        # Verificar si las filas tienen fechas propias
        tiene_fechas_excel = any(r["fecha_inicio"] and r["fecha_fin"] for r in self._rows)

        # Si ninguna fila trae fechas Y el usuario no ingresó el rango global → error
        if not tiene_fechas_excel and (not fi_global or not ff_global):
            QMessageBox.warning(self, "Fechas requeridas",
                "El archivo no contiene columnas FECHA INICIO / FECHA FIN.\n"
                "Ingresa el rango de fechas global arriba.")
            return

        self.log.append(f"[INICIO] Descarga masiva: {len(self._rows)} pacientes")
        if tiene_fechas_excel:
            self.log.append("[INFO] Usando fechas individuales del Excel por paciente")
        else:
            self.log.append(f"[INFO] Usando rango global: {fi_global} → {ff_global}")

        self.progress.setValue(0)
        self.progress.setMaximum(len(self._rows))
        for i, row in enumerate(self._rows):
            fi = row["fecha_inicio"] or fi_global
            ff = row["fecha_fin"]    or ff_global
            self.tabla.setItem(i, 4, QTableWidgetItem("En cola..."))
            self.log.append(f"[{i+1}/{len(self._rows)}] Paciente {row['id']} | {fi} → {ff}")
            self.progress.setValue(i + 1)
        self.log.append("[NOTA] Conectar cada item con bot_engine.Bot para ejecucion real.")

    def _open(self):
        d = _ROOT_DIR / "downloads" / "hc"
        d.mkdir(parents=True, exist_ok=True)
        os.startfile(str(d))


# ===========================================================================
# Ventana Principal
# ===========================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"BOT360  v{VERSION}  —  Panel de Control")
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(DARK_STYLE)
        self._build_ui()
        self._build_menu()
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage(f"BOT360 v{VERSION} — Listo")
        self.show()

    def _build_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        vl = QVBoxLayout(cw)
        vl.setContentsMargins(8, 8, 8, 4)
        tabs = QTabWidget()
        vl.addWidget(tabs)
        self.tab_dash  = DashboardTab()
        self.tab_cred  = CredencialesTab()
        self.tab_nav   = NavegadoresTab()
        self.tab_ag    = AgendaTab()
        self.tab_hc    = HCTab()
        tabs.addTab(self.tab_dash,  "Dashboard")
        tabs.addTab(self.tab_cred,  "Credenciales")
        tabs.addTab(self.tab_nav,   "Navegadores")
        tabs.addTab(self.tab_ag,    "Crear Agenda")
        tabs.addTab(self.tab_hc,    "Historia Clinica")

    def _build_menu(self):
        mb = self.menuBar()
        ma = mb.addMenu("Archivo")
        ma.addAction("Guardar Todo", self._save_all)
        ma.addSeparator()
        ma.addAction("Salir", self.close)
        mh = mb.addMenu("Herramientas")
        mh.addAction("Verificar Navegadores", self.tab_nav.check_browsers)
        mh.addAction("Abrir Logs", lambda: os.startfile(str(_ROOT_DIR / "logs" / "runtime")))
        mh.addAction("Abrir Descargas", lambda: os.startfile(str(_ROOT_DIR / "downloads")))
        mh.addSeparator()
        mh.addAction("Buscar Actualizaciones", self._check_updates)
        my = mb.addMenu("Ayuda")
        my.addAction("Acerca de", self._about)

    def _save_all(self):
        self.tab_cred.save_main_cred()
        self.tab_cred._save_hc()
        self.tab_nav.save_config()
        self.statusBar().showMessage("Todo guardado")

    def _check_updates(self):
        self.statusBar().showMessage("Verificando actualizaciones...")
        UPDATE_URL = "https://api.github.com/repos/PabloGra77/BOT-HC/releases/latest"

        def do_check():
            try:
                import urllib.request
                import json as _json
                import tempfile

                with urllib.request.urlopen(UPDATE_URL, timeout=8) as resp:
                    data = _json.loads(resp.read().decode())

                latest_tag = data.get("tag_name", "")
                latest = latest_tag.lstrip("v")

                if not latest or latest == VERSION:
                    QTimer.singleShot(0, lambda: self.statusBar().showMessage(
                        f"Ya tienes la versión más reciente (v{VERSION})"))
                    return

                # Buscar el asset .exe directo (onefile build)
                assets = data.get("assets", [])
                exe_asset = next(
                    (a for a in assets if a.get("name", "").lower().endswith(".exe")), None
                )
                download_url = exe_asset["browser_download_url"] if exe_asset else None
                total_size   = exe_asset.get("size", 0) if exe_asset else 0

                def ask():
                    self.statusBar().showMessage(f"Nueva versión disponible: v{latest}")
                    size_mb = f"{total_size / 1_048_576:.1f} MB" if total_size else ""
                    if not download_url:
                        QMessageBox.information(self, "Actualización disponible",
                            f"Nueva versión: v{latest}\nActual: v{VERSION}\n\n"
                            "No se encontró el .exe para descarga directa.\n"
                            "Descárgala en:\nhttps://github.com/PabloGra77/BOT-HC/releases")
                        return

                    r = QMessageBox.question(self, "Actualización disponible",
                        f"Nueva versión: v{latest}  (actual: v{VERSION})\n"
                        f"Tamaño: {size_mb}\n\n"
                        "¿Actualizar ahora?\n\n"
                        "El programa se cerrará, se actualizará y se reabrirá automáticamente.\n"
                        "Tu configuración (config.json) no se toca.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if r != QMessageBox.StandardButton.Yes:
                        return

                    def download_and_replace():
                        try:
                            # 1. Descargar nuevo .exe a archivo temporal
                            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix="BOT360_new_")
                            os.close(tmp_fd)
                            received = 0

                            with urllib.request.urlopen(download_url, timeout=120) as dl, \
                                 open(tmp_path, "wb") as f:
                                while True:
                                    chunk = dl.read(65536)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                                    received += len(chunk)
                                    if total_size:
                                        pct = int(received * 100 / total_size)
                                        QTimer.singleShot(0, lambda p=pct:
                                            self.statusBar().showMessage(
                                                f"Descargando actualización... {p}%"))

                            # 2. Obtener ruta del .exe actual
                            current_exe = Path(sys.executable if getattr(sys, "frozen", False)
                                               else __file__).resolve()

                            # 3. Crear script batch que espera cierre, reemplaza y relanza
                            bat_fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="bot360_upd_")
                            os.close(bat_fd)
                            bat_content = (
                                "@echo off\n"
                                "timeout /t 2 /nobreak >nul\n"
                                f'move /Y "{tmp_path}" "{current_exe}"\n'
                                f'start "" "{current_exe}"\n'
                                f'del "%~f0"\n'
                            )
                            with open(bat_path, "w") as bf:
                                bf.write(bat_content)

                            # 4. Lanzar script y cerrar app
                            subprocess.Popen(
                                ["cmd", "/c", bat_path],
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                            QTimer.singleShot(0, lambda: QApplication.instance().quit())

                        except Exception as ex:
                            QTimer.singleShot(0, lambda: (
                                self.statusBar().showMessage(f"Error al actualizar: {ex}"),
                                QMessageBox.critical(self, "Error de actualización",
                                    f"No se pudo completar la actualización:\n{ex}"),
                            ))

                    threading.Thread(target=download_and_replace, daemon=True).start()

                QTimer.singleShot(0, ask)

            except Exception as ex:
                QTimer.singleShot(0, lambda: self.statusBar().showMessage(
                    f"Error al verificar: {ex}"))

        threading.Thread(target=do_check, daemon=True).start()

    def _about(self):
        QMessageBox.about(
            self, "Acerca de BOT360",
            f"<b>BOT360</b> v{VERSION}<br><br>"
            "Automatizacion de Agendas y Gestion de HC.<br>"
            "Python 3.9+  |  PyQt6  |  Selenium<br><br>"
            "Licencia: MIT"
        )

    def closeEvent(self, event):
        r = QMessageBox.question(
            self, "Salir", "Deseas cerrar BOT360?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        event.accept() if r == QMessageBox.StandardButton.Yes else event.ignore()


# ===========================================================================
# Entry point
# ===========================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BOT360")
    app.setApplicationVersion(VERSION)
    win = MainWindow()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
