from flask import Blueprint, render_template_string, send_file
import json
import pandas as pd
import io
from datetime import datetime
from ..api.agenda_routes import continuar_job_api, crear_agenda, descargar_hc, estado_agenda, detener_job_api
from ..config import Config


ui_bp = Blueprint("ui", __name__)


TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>BOT MASTER V9.3</title>
  <style>
    :root {
      --bg: #f4efe4;
      --panel: rgba(255, 252, 246, 0.9);
      --panel-strong: #fffaf0;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: rgba(120, 113, 108, 0.18);
      --brand: #0f766e;
      --brand-dark: #115e59;
      --accent: #ea580c;
      --accent-soft: #fff1e8;
      --success: #15803d;
      --danger: #b91c1c;
      --warning: #b45309;
      --shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
      --radius: 22px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 28px;
      color: var(--ink);
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(234, 88, 12, 0.14), transparent 24%),
        linear-gradient(180deg, #f7f1e8 0%, #f2ece1 100%);
    }
    .app-shell {
      max-width: 1180px;
      margin: 0 auto;
      display: grid;
      gap: 22px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 20px;
      background: linear-gradient(135deg, rgba(255,250,240,0.96), rgba(249, 243, 229, 0.92));
      border: 1px solid rgba(255,255,255,0.65);
      border-radius: 28px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .hero-copy {
      padding: 28px;
      position: relative;
    }
    .brand-stamp {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      margin-top: 18px;
      padding: 14px 18px;
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(15,118,110,0.14), rgba(234,88,12,0.14));
      border: 1px solid rgba(15,118,110,0.14);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
    }
    .brand-mark {
      width: 44px;
      height: 44px;
      display: grid;
      place-items: center;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--brand), var(--brand-dark));
      color: white;
      font-size: 20px;
      font-weight: 900;
      letter-spacing: 0.08em;
    }
    .brand-stamp strong {
      display: block;
      font-size: 22px;
      letter-spacing: -0.02em;
      color: var(--brand-dark);
    }
    .brand-stamp span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.1);
      color: var(--brand-dark);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    h1 {
      margin: 16px 0 10px;
      font-size: clamp(30px, 5vw, 50px);
      line-height: 0.98;
      letter-spacing: -0.03em;
    }
    .hero p {
      margin: 0;
      max-width: 64ch;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.7;
    }
    .hero-panel {
      padding: 24px;
      background: linear-gradient(160deg, rgba(15,118,110,0.95), rgba(17,94,89,0.95));
      color: #ecfeff;
      display: grid;
      gap: 14px;
      align-content: center;
    }
    .hero-panel h3 {
      margin: 0;
      font-size: 18px;
    }
    .hero-panel p {
      color: rgba(236, 254, 255, 0.84);
      font-size: 14px;
    }
    .hero-list {
      display: grid;
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
      font-size: 14px;
    }
    .hero-list li {
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255,255,255,0.1);
    }
    .tabs {
      display: inline-flex;
      gap: 10px;
      padding: 8px;
      border-radius: 18px;
      background: rgba(255,255,255,0.65);
      border: 1px solid rgba(255,255,255,0.7);
      box-shadow: var(--shadow);
      width: fit-content;
    }
    .tab {
      padding: 12px 18px;
      border-radius: 14px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 700;
      color: var(--muted);
      transition: 160ms ease;
    }
    .tab:hover { background: rgba(15, 118, 110, 0.08); color: var(--brand-dark); }
    .tab.active {
      background: linear-gradient(135deg, var(--brand), var(--brand-dark));
      color: white;
      box-shadow: 0 10px 18px rgba(15, 118, 110, 0.2);
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    .layout {
      display: grid;
      grid-template-columns: 1.45fr 0.95fr;
      gap: 22px;
      align-items: start;
    }
    .panel {
      background: var(--panel);
      backdrop-filter: blur(12px);
      border-radius: var(--radius);
      border: 1px solid rgba(255,255,255,0.7);
      box-shadow: var(--shadow);
      padding: 24px;
    }
    .panel-title {
      margin: 0 0 8px;
      font-size: 24px;
      letter-spacing: -0.02em;
    }
    .panel-subtitle {
      margin: 0 0 22px;
      color: var(--muted);
      line-height: 1.65;
      font-size: 14px;
    }
    .highlight-box {
      padding: 18px;
      background: linear-gradient(180deg, #fffdf8, #fff8ee);
      border: 1px solid #f0e4d0;
      border-radius: 18px;
      margin-bottom: 18px;
    }
    .highlight-box strong { color: var(--brand-dark); }
    .form-grid {
      display: grid;
      gap: 14px;
    }
    .form-group { display: grid; gap: 8px; }
    label {
      display: block;
      font-size: 13px;
      font-weight: 700;
      color: #3f3f46;
      letter-spacing: 0.01em;
    }
    input, select, textarea {
      width: 100%;
      padding: 13px 14px;
      border-radius: 14px;
      border: 1px solid #d6d3d1;
      background: rgba(255,255,255,0.92);
      color: var(--ink);
      font-size: 14px;
      transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }
    textarea { min-height: 132px; resize: vertical; }
    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: rgba(15,118,110,0.55);
      box-shadow: 0 0 0 4px rgba(15,118,110,0.12);
      transform: translateY(-1px);
    }
    .action-row, .controls-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .button, button {
      appearance: none;
      border: none;
      border-radius: 16px;
      padding: 14px 18px;
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
    }
    .button:hover, button:hover { transform: translateY(-1px); }
    .button:disabled, button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
    .button-primary {
      background: linear-gradient(135deg, var(--brand), var(--brand-dark));
      color: white;
      box-shadow: 0 14px 26px rgba(15,118,110,0.18);
      flex: 1;
    }
    .button-secondary {
      background: white;
      color: var(--brand-dark);
      border: 1px solid rgba(15,118,110,0.18);
      flex: 1;
    }
    .button-warn {
      background: #fff5f5;
      color: var(--danger);
      border: 1px solid rgba(185,28,28,0.16);
      flex: 1;
    }
    .button-success {
      background: #effcf4;
      color: var(--success);
      border: 1px solid rgba(21,128,61,0.16);
      flex: 1;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .metric {
      padding: 16px;
      border-radius: 18px;
      background: var(--panel-strong);
      border: 1px solid #efe7d8;
    }
    .metric-label {
      margin: 0 0 6px;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 800;
    }
    .metric-value {
      margin: 0;
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }
    .metric-detail {
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .status-card {
      padding: 20px;
      border-radius: 22px;
      background: linear-gradient(180deg, #fffdf8, #fff7eb);
      border: 1px solid #f0e4d0;
      display: grid;
      gap: 14px;
    }
    .status-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .status-badge.pending { background: #fff8db; color: #a16207; }
    .status-badge.running { background: #e0f2fe; color: #075985; }
    .status-badge.stopping { background: #ffedd5; color: #c2410c; }
    .status-badge.stopped { background: #fee2e2; color: #b91c1c; }
    .status-badge.finished { background: #dcfce7; color: #15803d; }
    .status-badge.error { background: #fee2e2; color: #991b1b; }
    .status-detail {
      margin: 0;
      color: #3f3f46;
      font-size: 14px;
      line-height: 1.65;
      min-height: 44px;
    }
    .progress-rail {
      width: 100%;
      height: 14px;
      border-radius: 999px;
      background: #ebe4d8;
      overflow: hidden;
    }
    .progress-fill {
      width: 0%;
      height: 100%;
      background: linear-gradient(90deg, var(--brand), var(--accent));
      border-radius: inherit;
      transition: width 300ms ease;
    }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 14px;
    }
    .status-item {
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.72);
      border: 1px solid #f2e8d7;
    }
    .status-item strong {
      display: block;
      margin-bottom: 5px;
      font-size: 11px;
      color: var(--muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .status-item span {
      font-size: 14px;
      word-break: break-word;
    }
    .manual-box {
      margin-top: 18px;
      border-radius: 18px;
      border: 1px solid #eadfcd;
      background: rgba(255,255,255,0.6);
      overflow: hidden;
    }
    .manual-box summary {
      cursor: pointer;
      padding: 16px 18px;
      font-weight: 800;
      list-style: none;
      color: var(--brand-dark);
    }
    .manual-box summary::-webkit-details-marker { display: none; }
    .manual-content { padding: 0 18px 18px; }
    .helper {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }
    .tiny-link {
      color: var(--brand);
      font-weight: 700;
      cursor: pointer;
    }
    .agenda-panel {
      max-width: 760px;
    }
    @media (max-width: 980px) {
      .hero, .layout { grid-template-columns: 1fr; }
      .metrics, .status-grid { grid-template-columns: 1fr; }
      body { padding: 16px; }
    }
  </style>
  <script>
    function openTab(tabName) {
      var i;
      var x = document.getElementsByClassName("tab-content");
      for (i = 0; i < x.length; i++) {
        x[i].style.display = "none";
        x[i].classList.remove("active");
      }
      var tabs = document.getElementsByClassName("tab");
      for (i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove("active");
      }
      document.getElementById(tabName).style.display = "block";
      document.getElementById(tabName).classList.add("active");
      document.getElementById("btn-" + tabName).classList.add("active");
    }

    function toggleOtro() {
      var sel = document.getElementById('sede-select');
      var otro = document.getElementById('sede-otro');
      if (sel.value === '__OTRO__') {
        otro.style.display = 'block';
        otro.required = true;
      } else {
        otro.style.display = 'none';
        otro.required = false;
      }
    }
    
    function toggleOtroServicio() {
      var sel = document.getElementById('servicio-select');
      var otro = document.getElementById('servicio-otro');
      if (sel.value === '__OTRO__') {
        otro.style.display = 'block';
        // otro.required = true; // Opcional si se quiere forzar
      } else {
        otro.style.display = 'none';
        // otro.required = false;
      }
    }
    
    document.addEventListener('DOMContentLoaded', function() {
        toggleOtro();
        toggleOtroServicio();
        openTab('hc');
    });
  </script>
</head>
<body>
  <div class="app-shell">
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Bot Master V9.3</div>
        <h1>Centro de ejecución para carga masiva y control del bot</h1>
        <p>
          Esta interfaz está optimizada para ejecutar el archivo Excel, descargar la plantilla actual,
          detener el bot de forma segura, reanudar la operación y ver una hora estimada de finalización
          mientras avanza la descarga.
        </p>
        <div class="brand-stamp">
          <div class="brand-mark">BM</div>
          <div>
            <strong>BOT MASTER V9.3</strong>
            <span>Panel principal de ejecución y control</span>
          </div>
        </div>
      </div>
      <aside class="hero-panel">
        <h3>Panel rápido</h3>
        <p>La vista prioriza el flujo de Historia Clínica por archivo adjunto y mantiene el control del job en tiempo real.</p>
        <ul class="hero-list">
          <li>Sube el Excel y ejecuta la carga masiva con un clic.</li>
          <li>Descarga la plantilla actualizada desde la misma pantalla.</li>
          <li>Visualiza pausa, reanudación, avance y hora estimada de término.</li>
        </ul>
      </aside>
    </section>

    <div class="tabs">
      <div id="btn-hc" class="tab" onclick="openTab('hc')">Historias Clínicas</div>
      <div id="btn-agenda" class="tab" onclick="openTab('agenda')">Agenda</div>
    </div>

    <div id="hc" class="tab-content">
      <div class="layout">
        <section class="panel">
          <h2 class="panel-title">Ejecutar archivo de descarga</h2>
          <p class="panel-subtitle">
            Usa esta sección para correr el archivo Excel del lote. El sistema mostrará el estado del bot,
            el progreso del archivo, la pausa o reanudación y una estimación del tiempo restante.
          </p>

          <div class="highlight-box">
            <strong>Formato recomendado del Excel</strong>
            <div class="helper">
              Columnas esperadas: <b>CC</b>, <b>SERVICIO</b>, <b>ESTRATEGIA</b>, <b>FECHA INICIO</b>, <b>FECHA FIN</b> y <b>NUMERO DE FACTURA</b>.
              Si un paciente tiene varios servicios, usa filas separadas.
            </div>
          </div>

          <form id="form-excel" class="form-grid">
            <div class="form-group">
              <label>Archivo Excel para ejecución masiva</label>
              <input type="file" name="archivo_excel" accept=".xlsx, .xls">
            </div>
            <div class="action-row">
              <button type="button" class="button button-primary" onclick="procesarExcel(this)">▶ Ejecutar archivo adjunto</button>
              <button type="button" class="button button-secondary" onclick="window.location.href='/descargar_plantilla'">Descargar plantilla nueva</button>
            </div>
          </form>

          <details class="manual-box">
            <summary>Ingreso manual de respaldo</summary>
            <div class="manual-content">
              <p class="helper">Si no vas a trabajar con Excel, puedes lanzar una descarga puntual desde aquí.</p>
              <form id="hc-form-manual" class="form-grid">
                <div class="form-group">
                  <label>Cédula(s) del paciente</label>
                  <textarea name="cedula" placeholder="Ingrese una cédula por línea..."></textarea>
                </div>
                <div class="form-group">
                  <label>Servicio</label>
                  <select id="servicio-select" name="servicio" onchange="toggleOtroServicio()">
                    {% for serv in servicios_hc %}
                      <option value="{{ serv }}">{{ serv }}</option>
                    {% endfor %}
                    <option value="__OTRO__">Otro...</option>
                  </select>
                  <input type="text" id="servicio-otro" name="servicio_otro" placeholder="Escriba el servicio si no está en la lista" style="display:none; margin-top: 6px;">
                </div>
                <div class="form-group">
                  <label>Fecha Inicio</label>
                  <input name="fecha_inicio" placeholder="Ej: 01/01/2024">
                </div>
                <div class="form-group">
                  <label>Fecha Fin <span class="tiny-link" onclick="setToday('fecha_fin')">usar fecha actual</span></label>
                  <input name="fecha_fin" id="fecha_fin" placeholder="Ej: 31/01/2024 o hoy">
                </div>
                <div class="form-group">
                  <label>Preferencia de descarga</label>
                  <div class="controls-row">
                    <label><input type="radio" name="estrategia" value="RECIENTE" checked> Más reciente</label>
                    <label><input type="radio" name="estrategia" value="ANTIGUA"> Más antigua</label>
                  </div>
                </div>
                <div class="form-group">
                  <label>Carpeta de descarga</label>
                  <input name="ruta_descarga" placeholder="C:\\Users\\Usuario\\Documents\\Historias">
                </div>
                <button type="button" class="button button-secondary" onclick="procesarManual(this)">▶ Ejecutar descarga manual</button>
              </form>
            </div>
          </details>
        </section>

        <aside class="panel">
          <h2 class="panel-title">Estado del bot</h2>
          <p class="panel-subtitle">Monitoreo de ejecución, avance del archivo y hora estimada de finalización.</p>

          <div class="metrics">
            <div class="metric">
              <p class="metric-label">Progreso</p>
              <p id="metric-progress" class="metric-value">0%</p>
              <div id="metric-counts" class="metric-detail">0 de 0 registros</div>
            </div>
            <div class="metric">
              <p class="metric-label">Hora estimada</p>
              <p id="metric-eta" class="metric-value">Sin cálculo</p>
              <div id="metric-elapsed" class="metric-detail">Tiempo transcurrido: 00:00</div>
            </div>
          </div>

          <div class="status-card">
            <div class="status-top">
              <div id="status-badge" class="status-badge pending">Esperando</div>
              <div id="current-job-chip" class="helper">Job: sin ejecutar</div>
            </div>

            <p id="status-detail" class="status-detail">Esperando que cargues el archivo Excel o ejecutes una descarga manual.</p>

            <div class="progress-rail">
              <div id="progress-fill" class="progress-fill"></div>
            </div>

            <div class="status-grid">
              <div class="status-item">
                <strong>Registro actual</strong>
                <span id="current-item">Sin actividad</span>
              </div>
              <div class="status-item">
                <strong>Última actualización</strong>
                <span id="updated-at">Sin datos</span>
              </div>
              <div class="status-item">
                <strong>Creado</strong>
                <span id="created-at">Sin datos</span>
              </div>
              <div class="status-item">
                <strong>Acción disponible</strong>
                <span id="action-hint">Listo para ejecutar</span>
              </div>
            </div>

            <div class="controls-row">
              <button id="btn-stop-bot" type="button" class="button button-warn" onclick="detenerBot()" style="display:none;">Detener bot</button>
              <button id="btn-continue-bot" type="button" class="button button-success" onclick="continuarDescarga()" style="display:none;">Reanudar descarga</button>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <div id="agenda" class="tab-content">
      <section class="panel agenda-panel">
        <h2 class="panel-title">Configurar agenda</h2>
        <p class="panel-subtitle">La descarga de HC queda como flujo principal; esta sección conserva la generación de agenda cuando la necesites.</p>
        <form id="agenda-form" class="form-grid">
          <div class="form-group">
            <label>Sede</label>
            <select id="sede-select" name="sede" onchange="toggleOtro()" required>
              {% for s in sedes %}
                <option value="{{ s }}">{{ s }}</option>
              {% endfor %}
              <option value="__OTRO__">Otro...</option>
            </select>
            <input type="text" id="sede-otro" name="sede_otro" placeholder="Escriba la sede" style="display:none; margin-top: 6px;">
          </div>
          <div class="form-group"><label>Cédula profesional</label><input name="cc" required></div>
          <div class="form-group"><label>Fecha (DD/MM/YYYY o hoy)</label><input name="fecha" required></div>
          <div class="form-group"><label>Hora inicio (HH:MM)</label><input name="hora_inicio" required></div>
          <div class="form-group"><label>Duración de cada cita (minutos)</label><input type="number" name="duracion_min" value="15" required></div>
          <div class="form-group"><label>Cantidad de citas</label><input type="number" name="cantidad" value="1" required></div>
          <button type="submit" class="button button-primary">Generar agenda</button>
        </form>
      </section>
    </div>
  </div>

  <script>
    function setToday(inputId) {
        const input = document.getElementById(inputId);
        if (input) {
            const today = new Date();
            const dd = String(today.getDate()).padStart(2, '0');
            const mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
            const yyyy = today.getFullYear();
            input.value = dd + '/' + mm + '/' + yyyy;
        }
    }

    const stopBtn = document.getElementById("btn-stop-bot");
    const continueBtn = document.getElementById("btn-continue-bot");
    const statusBadge = document.getElementById("status-badge");
    const statusDetail = document.getElementById("status-detail");
    const progressFill = document.getElementById("progress-fill");
    const metricProgress = document.getElementById("metric-progress");
    const metricCounts = document.getElementById("metric-counts");
    const metricEta = document.getElementById("metric-eta");
    const metricElapsed = document.getElementById("metric-elapsed");
    const currentItem = document.getElementById("current-item");
    const updatedAt = document.getElementById("updated-at");
    const createdAt = document.getElementById("created-at");
    const actionHint = document.getElementById("action-hint");
    const currentJobChip = document.getElementById("current-job-chip");
    const JOB_STORAGE_KEY = "botmaster_active_job_id";
    let currentJobId = null;
    let currentMonitor = null;

    function saveCurrentJobId(jobId) {
      currentJobId = jobId || null;
      if (currentJobId) {
        window.localStorage.setItem(JOB_STORAGE_KEY, currentJobId);
      } else {
        window.localStorage.removeItem(JOB_STORAGE_KEY);
      }
    }

    function restoreCurrentJobId() {
      const saved = window.localStorage.getItem(JOB_STORAGE_KEY);
      if (saved) {
        currentJobId = saved;
      }
      return currentJobId;
    }

    function parseIsoDate(value) {
      if (!value) return null;
      const parsed = new Date(value);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    }

    function formatClock(dateObj) {
      if (!dateObj) return "Sin datos";
      return dateObj.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
    }

    function formatDateTime(dateObj) {
      if (!dateObj) return "Sin datos";
      return dateObj.toLocaleString('es-CO', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
    }

    function formatDuration(ms) {
      if (!ms || ms < 0) return "00:00";
      const totalSeconds = Math.floor(ms / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      if (hours > 0) {
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      }
      return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    function setStatusBadge(status) {
      const normalized = (status || 'pending').toLowerCase();
      statusBadge.className = `status-badge ${normalized}`;
      const labels = {
        pending: 'En cola',
        running: 'En ejecución',
        stopping: 'Deteniendo',
        stopped: 'Detenido',
        finished: 'Finalizado',
        error: 'Error'
      };
      statusBadge.textContent = labels[normalized] || normalized;
    }

    function updateDashboard(job, jobId) {
      const status = (job.status || 'pending').toLowerCase();
      const total = Number(job.progress_total || 0);
      const completed = Number(job.progress_completed || 0);
      const percent = Number(job.progress_percent || (total > 0 ? Math.round((completed / total) * 100) : 0));
      const created = parseIsoDate(job.created_at);
      const updated = parseIsoDate(job.updated_at);
      const now = new Date();
      const elapsedMs = created ? Math.max(0, now - created) : 0;

      setStatusBadge(status);
      currentJobChip.textContent = `Job: ${jobId || 'sin ejecutar'}`;
      statusDetail.innerHTML = job.detail || 'Sin detalle';
      metricProgress.textContent = `${percent}%`;
      metricCounts.textContent = `${completed} de ${total} registros`;
      progressFill.style.width = `${Math.max(0, Math.min(percent, 100))}%`;
      currentItem.textContent = job.current_item || 'Sin actividad';
      updatedAt.textContent = formatDateTime(updated);
      createdAt.textContent = formatDateTime(created);
      metricElapsed.textContent = `Tiempo transcurrido: ${formatDuration(elapsedMs)}`;

      if (status === 'stopped') {
        actionHint.textContent = 'Puedes reanudar la descarga';
      } else if (status === 'running' || status === 'stopping') {
        actionHint.textContent = 'El bot está trabajando sobre el archivo';
      } else if (status === 'finished') {
        actionHint.textContent = 'La descarga ya terminó';
      } else if (status === 'error') {
        actionHint.textContent = 'Revisa el detalle o reanuda el job';
      } else {
        actionHint.textContent = 'Listo para ejecutar';
      }

      if ((status === 'running' || status === 'stopping') && completed > 0 && total > completed && created) {
        const avgPerItem = elapsedMs / completed;
        const remainingMs = avgPerItem * (total - completed);
        const etaDate = new Date(now.getTime() + remainingMs);
        metricEta.textContent = formatClock(etaDate);
      } else if ((status === 'running' || status === 'pending') && total > 0 && completed === 0) {
        const fallbackMsPerItem = 90000;
        const etaDate = new Date(now.getTime() + (total * fallbackMsPerItem));
        metricEta.textContent = `${formatClock(etaDate)} aprox.`;
      } else if (status === 'finished') {
        metricEta.textContent = 'Finalizado';
      } else if (status === 'stopped') {
        metricEta.textContent = 'En pausa';
      } else if (status === 'error') {
        metricEta.textContent = 'Sin cálculo';
      } else {
        metricEta.textContent = 'Calculando...';
      }
    }

    // AGENDA SUBMIT
    const agendaForm = document.getElementById("agenda-form");
    agendaForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      setStatusBadge('pending');
      statusDetail.textContent = 'Enviando solicitud de agenda...';
      const fd = new FormData(agendaForm);
      const data = Object.fromEntries(fd.entries());
      if (data.sede === "__OTRO__") {
        data.sede = (data.sede_otro || "").trim();
      }
      data.duracion_min = parseInt(data.duracion_min, 10);
      data.cantidad = parseInt(data.cantidad, 10);
      
      await submitJob("/ui/jobs", data, false);
    });

    // HC SUBMIT - (Código antiguo eliminado para evitar conflictos)
    // Las funciones procesarExcel y procesarManual manejan el envío directamente.

    // Nueva función para procesar EXCEL
    async function procesarExcel(btn) {
        console.log(">>> procesarExcel");
        // Referencias a elementos
        const formEl = document.getElementById("form-excel");
        const fileInput = formEl.querySelector('input[name="archivo_excel"]');
        
        // Validación
        if (!fileInput.files || fileInput.files.length === 0) {
          alert("⚠️ ERROR: Debe seleccionar un archivo Excel primero.");
            fileInput.style.border = "2px solid red";
            setTimeout(() => fileInput.style.border = "", 3000);
            return;
        }

        // UI Feedback
        const originalText = btn.innerText;
        btn.disabled = true;
        btn.innerText = "⏳ Subiendo...";
        setStatusBadge('pending');
        statusDetail.textContent = 'Subiendo archivo Excel y preparando la ejecución...';

        try {
            const fd = new FormData(formEl);
            // Agregar campos opcionales del otro formulario si se desea, o dejar que el backend maneje defaults
            // Para Excel, la estrategia suele venir dentro del Excel, pero podemos mandar un default si se quiere.
            
            await submitJob("/ui/hc", fd, true);
        } catch (e) {
            console.error(e);
            alert("Error al enviar Excel: " + e.message);
          updateDashboard({ status: 'error', detail: `Error al enviar Excel: ${e.message}` }, currentJobId);
        } finally {
            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = originalText;
            }, 3000);
        }
    }

    // Nueva función para procesar MANUAL
    async function procesarManual(btn) {
        console.log(">>> procesarManual");
        // Referencias
        const formEl = document.getElementById("hc-form-manual");
        const cedulaInput = formEl.querySelector('textarea[name="cedula"]');
        
        // Validación
        if (!cedulaInput.value || cedulaInput.value.trim().length === 0) {
          alert("⚠️ ERROR: Debe ingresar al menos una cédula.");
            cedulaInput.style.border = "2px solid red";
            setTimeout(() => cedulaInput.style.border = "", 3000);
            return;
        }

        // UI Feedback
        const originalText = btn.innerText;
        btn.disabled = true;
        btn.innerText = "⏳ Enviando...";
        setStatusBadge('pending');
        statusDetail.textContent = 'Enviando solicitud manual...';

        try {
            const fd = new FormData(formEl);
            
            // Ajuste manual para servicio "otro"
            const servicio = fd.get("servicio");
            const servicioOtro = fd.get("servicio_otro");
            if (servicio === "__OTRO__") {
                fd.set("servicio", (servicioOtro || "").trim());
            }

            await submitJob("/ui/hc", fd, true);
        } catch (e) {
            console.error(e);
            alert("Error al enviar solicitud manual: " + e.message);
          updateDashboard({ status: 'error', detail: `Error al enviar solicitud manual: ${e.message}` }, currentJobId);
        } finally {
            setTimeout(() => {
                btn.disabled = false;
                btn.innerText = originalText;
            }, 3000);
        }
    }

    async function submitJob(url, data, isFormData = false) {
      console.log(">>> [DEBUG] Entrando a submitJob:", url);
      try {
        const headers = {};
        
        let body = data;
        if (!isFormData) {
            headers["Content-Type"] = "application/json";
            body = JSON.stringify(data);
        }

        console.log(">>> [DEBUG] Ejecutando fetch...");
        const resp = await fetch(url, {
            method: "POST",
            headers: headers,
            body: body
        });
        
        console.log(">>> [DEBUG] Respuesta recibida:", resp.status);
        const bodyResp = await resp.json();
        
        if (!resp.ok) {
            console.error(">>> [DEBUG] Error en API:", bodyResp);
            updateDashboard({ status: 'error', detail: bodyResp.error || 'desconocido' }, currentJobId);
            return;
        }
        
        console.log(">>> [DEBUG] Solicitud exitosa, Job ID:", bodyResp.job_id);
        saveCurrentJobId(bodyResp.job_id);
        stopBtn.style.display = "block";
        continueBtn.style.display = "none";
        updateDashboard({ status: 'pending', detail: 'Solicitud aceptada. Esperando respuesta del servidor...' }, bodyResp.job_id);
        monitorJob(bodyResp.job_id);
      } catch (err) {
          console.error(">>> [DEBUG] Excepción en submitJob:", err);
          updateDashboard({ status: 'error', detail: `Error de red: ${err.message}` }, currentJobId);
      }
    }

    function monitorJob(jobId) {
      if (currentMonitor) {
        clearInterval(currentMonitor);
      }
      currentMonitor = setInterval(async () => {
        try {
            const r = await fetch("/ui/jobs/" + jobId);
            const b = await r.json();
            updateDashboard(b, jobId);

            if (b.status === "pending" || b.status === "running" || b.status === "stopping") {
              stopBtn.style.display = "block";
              continueBtn.style.display = "none";
            } else if (b.status === "finished") {
              stopBtn.style.display = "none";
              continueBtn.style.display = "none";
              saveCurrentJobId(jobId);
              clearInterval(currentMonitor);
              currentMonitor = null;
            } else if (b.status === "stopped" || b.status === "error") {
              stopBtn.style.display = "none";
              continueBtn.style.display = "block";
              saveCurrentJobId(jobId);
              clearInterval(currentMonitor);
              currentMonitor = null;
            }
        } catch (err) {
            console.error("Error monitoreando:", err);
            updateDashboard({ status: 'error', detail: `Error de conexión: ${err.message}` }, jobId);
            clearInterval(currentMonitor);
            currentMonitor = null;
        }
      }, 3000);
    }

    async function detenerBot() {
      if (!currentJobId) {
        alert("No hay un job activo para detener.");
        return;
      }
      try {
        const resp = await fetch(`/ui/jobs/${currentJobId}/stop`, { method: "POST" });
        const body = await resp.json();
        if (!resp.ok) {
          alert(body.error || "No se pudo detener el job.");
          return;
        }
        updateDashboard({ status: 'stopping', detail: body.message }, currentJobId);
      } catch (err) {
        alert("Error enviando detención: " + err.message);
      }
    }

    async function continuarDescarga() {
      if (!currentJobId) {
        alert("No hay un job base para continuar.");
        return;
      }
      try {
        const resp = await fetch(`/ui/jobs/${currentJobId}/continue`, { method: "POST" });
        const body = await resp.json();
        if (!resp.ok) {
          alert(body.error || "No se pudo continuar el job.");
          return;
        }
        saveCurrentJobId(body.job_id);
        stopBtn.style.display = "block";
        continueBtn.style.display = "none";
        updateDashboard({ status: 'pending', detail: `Continuación iniciada. Nuevo Job ID: ${body.job_id}` }, body.job_id);
        monitorJob(body.job_id);
      } catch (err) {
        alert("Error continuando descarga: " + err.message);
      }
    }

    document.addEventListener('DOMContentLoaded', async function() {
      const restoredJobId = restoreCurrentJobId();
      if (!restoredJobId) {
        updateDashboard({ status: 'pending', detail: 'Carga un archivo Excel para iniciar una ejecución nueva.' }, null);
        return;
      }
      try {
        const resp = await fetch(`/ui/jobs/${restoredJobId}`);
        if (!resp.ok) {
          saveCurrentJobId(null);
          updateDashboard({ status: 'pending', detail: 'No hay un job activo restaurable. Puedes iniciar uno nuevo.' }, null);
          return;
        }
        const job = await resp.json();
        updateDashboard(job, restoredJobId);
        if (["pending", "running", "stopping"].includes((job.status || '').toLowerCase())) {
          stopBtn.style.display = "block";
          continueBtn.style.display = "none";
          monitorJob(restoredJobId);
        } else if (["stopped", "error"].includes((job.status || '').toLowerCase())) {
          stopBtn.style.display = "none";
          continueBtn.style.display = "block";
        } else {
          stopBtn.style.display = "none";
          continueBtn.style.display = "none";
        }
      } catch (error) {
        updateDashboard({ status: 'error', detail: `No fue posible restaurar el estado del job: ${error.message}` }, restoredJobId);
      }
    });
  </script>
</body>
</html>
"""


@ui_bp.route("/", methods=["GET"])
def index():
    sedes = []
    try:
        with open(Config.CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            sedes = cfg.get("sedes", [])
    except Exception:
        sedes = []
    if not sedes:
        sedes = [
            "RM MANIZALES",
            "COMPLEJO CARCELARIO Y PENITENCIARIO BOGOTA",
            "CMS BARRANQUILLA",
            "COMPLEJO CARCELARIO Y PENITENCIARIO IBAGUE",
            "ADMINISTRATIVA-REGIONAL CENTRAL",
            "CAMIS ACACIAS",
        ]
        
    servicios_hc = [
        "Todos",
        "ADOLESCENCIA ENFERMERIA",
        "ADOLESCENCIA MEDICO",
        "ADULTEZ ENFERMERIA",
        "ADULTEZ MEDICO",
        "ANESTESIOLOGIA",
        "ATENCION DEL RECIEN NACIDO",
        "ATENCION POST-PARTO",
        "CARDIOLOGIA",
        "CIRUGIA CARDIOVASCULAR",
        "CIRUGIA GENERAL",
        "CIRUGIA VASCULAR",
        "CITOLOGIA",
        "CONSULTA AGUDEZA VISUAL",
        "CONSULTA DE MAMA",
        "CONSULTA DE PROSTATA",
        "CONSULTA ENFERMERIA",
        "CONSULTA PRECONCEPCIONAL",
        "CONSULTA PRIORITARIA",
        "CONSULTA PRIORITARIA ODONTOLOGÍA GENERAL",
        "CONTROL PRENATAL",
        "DERMATOLOGIA",
        "ENDOCRINOLOGIA",
        "ENFERMERA SM",
        "ENFERMERA TB",
        "ENFERMERA VIH",
        "EVOLUCION POR PROFESIONAL- FISIOTERAPIA SM",
        "EXAMEN MEDICO DE INGRESO EMI",
        "EXAMEN MEDICO DE TRASLADO",
        "EXAMEN MÉDICO EGRESO -EME",
        "FISIATRIA",
        "GASTROENTEROLOGIA",
        "GERIATRIA",
        "GINECOLOGIA",
        "INFECTOLOGIA TB",
        "INFECTOLOGIA VIH",
        "INTERPRETACION DE RESULTADOS",
        "INTERPRETACION DE RESULTADOS MEDICINA FAMILIAR",
        "JUVENTUD ENFERMERIA",
        "JUVENTUD MEDICO",
        "LACTANCIA MATERNA",
        "MEDICINA FAMILIAR",
        "MEDICINA GENERAL",
        "MEDICINA GENERAL TB",
        "MEDICINA GENERAL VIH",
        "MEDICINA INTERNA",
        "MEDICO GENERAL SM",
        "NEUMOLOGIA",
        "NEUROCIRUGIA",
        "NEUROLOGIA",
        "NEUROLOGIA SM",
        "NUTRICION",
        "OBSTETRICIA",
        "ODONTOLOGIA",
        "ODONTOLOGIA ESP",
        "OFTALMOLOGIA",
        "OPTOMETRIA",
        "ORTOPEDIA",
        "OTORRINOLARINGOLOGIA",
        "PEDIATRIA",
        "PLANIFICACION FAMILIAR",
        "PRIMERA INFANCIA ENFERMERIA",
        "PRIMERA INFANCIA MEDICO",
        "PROCEDIMIENTOS ENF",
        "PROCEDIMIENTOS MEDICOS",
        "PSICOEDUCACION SM",
        "PSICOLOGIA",
        "PSICOLOGIA CONTROL SM",
        "PSICOLOGIA PRIMERA VEZ SM",
        "PSICOLOGIA SM",
        "PSICOLOGIA TB",
        "PSICOLOGIA VIH",
        "PSIQUIATRIA",
        "PSIQUIATRIA SM",
        "RCV MEDICINA INTERNA",
        "REMISION AL PROBRAMA VIH",
        "REMISION AL PROGRAMA TB",
        "REUMATOLOGIA",
        "RIESGO CARDIOVASCULAR ENFERMERIA",
        "RIESGO CARDIOVASCULAR MEDICO",
        "SALUD ORAL",
        "TERAPIA FISICA",
        "TERAPIA FISICA SM",
        "TERAPIA OCUPACIONAL",
        "TERAPIA OCUPACIONAL SM",
        "TM CARDIOLOGIA",
        "TM CIRUGIA GENERAL",
        "TM DERMATOLOGIA",
        "TM ENDOCRINO",
        "TM GASTROENTEROLOGIA",
        "TM GINECOLOGIA",
        "TM MEDICINA FAMILIAR",
        "TM MEDICINA INTERNA",
        "TM NEUMOLOGIA",
        "TM NUTRICION",
        "TM OBSTETRICIA",
        "TM ODONTOLOGIA ESP",
        "TM OFTALMOLOGIA",
        "TM ORTOPEDIA",
        "TM PEDIATRIA",
        "TM PSICOLOGIA",
        "TM PSIQUIATRIA",
        "TM TERAPIA OCUPACIONAL",
        "TM TRABAJO SOCIAL",
        "TM UROLOGIA",
        "TRABAJO SOCIAL",
        "TRABAJO SOCIAL SM",
        "TRABAJO SOCIAL TB",
        "TRABAJO SOCIAL VIH",
        "UROLOGIA",
        "VALORACION",
        "VALORACION FISIOTERAPIA",
        "VALORACION ODONTOLOGIA EGRESO VOE",
        "VALORACION ODONTOLOGIA INGRESO VOI",
        "VALORACION ODONTOLOGICA DE TRASLADO",
        "VALORACION POR PROFESIONAL-FISIOTERAPIA SM",
        "VALORACION PPL MG",
        "VALORACION PPL ODON",
        "VALORACION PPL PSICOLOGIA",
        "VALORACION PSICOLOGIA DE INGRESO -VAPSI SM",
        "VEJEZ ENFERMERIA",
        "VEJEZ MEDICO"
    ]

    return render_template_string(TEMPLATE, sedes=sedes, servicios_hc=servicios_hc)


@ui_bp.route("/ui/jobs", methods=["POST"])
def submit_agenda_from_ui():
    return crear_agenda.__wrapped__()


@ui_bp.route("/ui/hc", methods=["POST"])
def submit_hc_from_ui():
    return descargar_hc.__wrapped__()


@ui_bp.route("/ui/jobs/<job_id>", methods=["GET"])
def ui_job_status(job_id):
    return estado_agenda.__wrapped__(job_id)


@ui_bp.route("/ui/jobs/<job_id>/stop", methods=["POST"])
def ui_stop_job(job_id):
  return detener_job_api.__wrapped__(job_id)


@ui_bp.route("/ui/jobs/<job_id>/continue", methods=["POST"])
def ui_continue_job(job_id):
  return continuar_job_api.__wrapped__(job_id)


@ui_bp.route("/descargar_plantilla", methods=["GET"])
def descargar_plantilla():
    # Crear un DataFrame de ejemplo
    data = {
      "CC": ["1234567890", "9876543210", "1122334455", "1122334455"],
      "SERVICIO": ["Todos", "", "ODONTOLOGIA", "PSICOLOGIA"],
      "ESTRATEGIA": ["RECIENTE", "", "RECIENTE", "RECIENTE"],
      "FECHA INICIO": ["01/01/2023", "", "01/01/2000", "01/01/2000"],
      "FECHA FIN": ["31/12/2023", "", "31/01/2000", "31/01/2000"],
      "NUMERO DE FACTURA": ["", "", "", ""]
    }
    df = pd.DataFrame(data)
    
    # Guardar en buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla')
        
        # Ajustar ancho de columnas (opcional, básico)
        worksheet = writer.sheets['Plantilla']
        worksheet.column_dimensions['A'].width = 20
        worksheet.column_dimensions['B'].width = 30
        worksheet.column_dimensions['C'].width = 15
        worksheet.column_dimensions['D'].width = 18
        worksheet.column_dimensions['E'].width = 15
        worksheet.column_dimensions['F'].width = 15
        worksheet.column_dimensions['G'].width = 20

        # Forzar formato de fecha DD/MM/AAAA en columnas FECHA INICIO (E) y FECHA FIN (F).
        for row_idx in range(2, worksheet.max_row + 1):
            for col in ("E", "F"):
                cell = worksheet[f"{col}{row_idx}"]
                value = cell.value
                if not value:
                    continue
                if isinstance(value, str):
                    try:
                        value = datetime.strptime(value.strip(), "%d/%m/%Y")
                        cell.value = value
                    except Exception:
                        # Si no es fecha válida (texto libre), se deja como está.
                        continue
                if isinstance(value, datetime):
                    cell.number_format = "DD/MM/YYYY"
        
    output.seek(0)
    
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="plantilla_pacientes_hc.xlsx"
    )
