import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import glob
import json

import pandas as pd

from ..config import Config
from ..domain.requests import AgendaRequest, HCRequest
from .excel_lookup import buscar_profesional_por_cc
from bot360_app.automation.loader import Bot
from bot360_app.common.job_config import build_agenda_runtime_config, cleanup_runtime_config
from bot360_app.common.settings import HC_OUTPUT_DIR


logger = logging.getLogger(__name__)
REINICIO_PREVENTIVO_CADA = 50
MAX_RECOVERY_ATTEMPTS = 3


def _normalizar_fecha_ddmmyyyy(valor):
    if valor is None:
        return None
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.strftime("%d/%m/%Y")

    s = str(valor).strip()
    if not s:
        return None
    if s.lower() == "hoy":
        return "hoy"

    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except Exception:
            pass

    try:
        # Importante: forzar dayfirst para no voltear día/mes.
        return pd.to_datetime(s, dayfirst=True).strftime("%d/%m/%Y")
    except Exception:
        return s


def _crear_bot_con_sesion(config_path, download_dir=None, browser_name="chrome", credential_override=None):
    bot = Bot(
        config_path=config_path,
        browser_name=browser_name,
        credential_override=credential_override,
    )
    bot.iniciar_navegador(download_dir=download_dir)
    bot.login()
    return bot


def _reiniciar_bot(bot, config_path, motivo, download_dir=None, browser_name="chrome", credential_override=None):
    logger.warning("Recuperando bot por falla transitoria: %s", motivo)
    if bot is not None:
        try:
            bot.cerrar()
        except Exception:
            logger.warning("Error cerrando bot durante recovery", exc_info=True)
    return _crear_bot_con_sesion(
        config_path=config_path,
        download_dir=download_dir,
        browser_name=browser_name,
        credential_override=credential_override,
    )


def _recuperar_o_reiniciar_bot(bot, config_path, motivo, download_dir=None, browser_name="chrome", credential_override=None):
    # Primero intentamos una recuperación suave para no cerrar/reabrir navegador en cada incidencia.
    if bot is not None:
        try:
            if bot.recuperar_pagina_y_sesion(motivo=motivo):
                return bot
        except Exception:
            logger.warning("Recovery suave falló; se intentará reinicio completo", exc_info=True)

    return _reiniciar_bot(
        bot,
        config_path=config_path,
        motivo=motivo,
        download_dir=download_dir,
        browser_name=browser_name,
        credential_override=credential_override,
    )


def _cargar_credenciales_hc():
    try:
        with open(Config.CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return [None]

    cred_list = cfg.get("credenciales_hc")
    if isinstance(cred_list, list) and cred_list:
        limpias = []
        for c in cred_list:
            if not isinstance(c, dict):
                continue
            usuario = str(c.get("usuario", "")).strip()
            contrasena = str(c.get("contrasena", "")).strip()
            url = str(c.get("url", cfg.get("credenciales", {}).get("url", ""))).strip()
            if not usuario or not contrasena or not url:
                continue
            limpias.append(
                {
                    "usuario": usuario,
                    "contrasena": contrasena,
                    "numero_verificacion": str(c.get("numero_verificacion", "")).strip(),
                    "url": url,
                }
            )
        if limpias:
            return limpias

    cred_default = cfg.get("credenciales")
    if isinstance(cred_default, dict) and cred_default:
        return [cred_default]
    return [None]


def _error_recuperable(exc):
    mensaje = str(exc or "").lower()
    claves = (
        "timeout",
        "unexpected alert",
        "unexpectedalertpresent",
        "alert text",
        "sesion ha caducado",
        "sesión ha caducado",
        "pagina se recargara",
        "página se recargará",
        "session",
        "invalid session",
        "stale",
        "disconnected",
        "target window already closed",
        "chrome not reachable",
        "web view not found",
        "no such window",
        "no such element",
        "pagina",
        "página",
        "driver",
        "navegador",
        "refresh",
    )
    return any(clave in mensaje for clave in claves)


def _asegurar_bot_listo(bot, modulo, motivo):
    if modulo == "hc":
        # Para HC hacemos chequeo liviano por cédula.
        # El mantenimiento preventivo profundo se ejecuta por lote cada REINICIO_PREVENTIVO_CADA.
        return bot.asegurar_sesion_activa(motivo=motivo)
    return bot.asegurar_sesion_activa(motivo=motivo)


def _tipo_codigo(tipo):
    t = str(tipo or "").upper().strip()
    if "VALORACION" in t or t == "VAL":
        return "VAL"
    if "EVOLUCION" in t or t == "EVO":
        return "EVO"
    if "PRIMERA VEZ" in t or t in ("PRIMERA", "PRV", "INGRESO"):
        return "PRV"
    return ""


def _servicio_codigo(servicio):
    s = str(servicio or "").upper()
    if "PSICOLOGIA PRIMERA VEZ" in s:
        return "VALPS"
    if "PSICOLOGIA CONTROL" in s:
        return "PS"
    if "PSIQUIATRIA" in s:
        return "PQ"
    if "TRABAJO SOCIAL" in s:
        return "TS"
    if "FISIOTERAPIA" in s or "FISIOTERAPEUTA" in s or "TERAPIA FISICA" in s:
        return "TF"
    if "ENFERMERIA" in s:
        return "MED"
    return "GEN"


def _nombre_carpeta_servicio(servicio):
    s = str(servicio or "").upper().strip()
    if not s:
        return "GEN"
    permitido = [ch for ch in s if ch.isalnum() or ch in (" ", "-", "_")]
    return (" ".join("".join(permitido).split()) or "GEN")[:60]


def _es_resultado_sin_hc(info):
    mensaje = str(info or "").lower()
    claves_sin_hc = (
        "sin registros",
        "no se encontraron registros",
        "no existen registros",
        "no hay datos",
        "sin resultados",
        "sin historia",
        "sin hc",
        "no se encontró información",
    )
    return any(clave in mensaje for clave in claves_sin_hc)


def _es_resultado_transitorio_hc(info):
    mensaje = str(info or "").lower()
    claves_transitorias = (
        "timeout",
        "unexpected alert",
        "sesion ha caducado",
        "sesión ha caducado",
        "pagina se recargara",
        "página se recargará",
        "405",
        "http 405",
        "no se detectó descarga",
        "no se detecto descarga",
        "driver no operativo",
        "sesion",
        "session",
        "chrome not reachable",
        "disconnected",
        "target window already closed",
        "web view not found",
        "pagina no disponible",
        "página no disponible",
        "conexión",
        "conexion",
    )
    return any(clave in mensaje for clave in claves_transitorias)


def _carpeta_descargas_usuario():
    # Prioridad Windows: USERPROFILE\Downloads
    userprofile = os.environ.get("USERPROFILE", "").strip()
    if userprofile:
        return os.path.join(userprofile, "Downloads")
    # Fallback multiplataforma
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _normalizar_ruta_descarga(ruta_descarga: str | None) -> str:
    base = (ruta_descarga or "").strip() or _carpeta_descargas_usuario()
    ruta_abs = os.path.abspath(base)

    # Permite rutas externas solo bajo bandera explícita.
    if os.environ.get("AGENDA_ALLOW_EXTERNAL_DOWNLOAD_PATH", "false").lower() == "true":
        return ruta_abs

    permitidas = [os.path.abspath(str(HC_OUTPUT_DIR)), os.path.abspath(_carpeta_descargas_usuario())]
    for root in permitidas:
        try:
            if os.path.commonpath([ruta_abs, root]) == root:
                return ruta_abs
        except ValueError:
            continue

    raise ValueError(
        "ruta_descarga fuera de ubicaciones permitidas. "
        "Use una ruta dentro de Downloads del usuario o downloads/hc del proyecto, "
        "o habilite AGENDA_ALLOW_EXTERNAL_DOWNLOAD_PATH=true"
    )


def _detener_solicitado(stop_event):
    return bool(stop_event is not None and stop_event.is_set())


def _ya_existe_descarga_tipo(download_dir, cedula, servicio, tipo_objetivo):
    cod_tipo = _tipo_codigo(tipo_objetivo)
    if not cod_tipo:
        return False
    cod_serv = _servicio_codigo(servicio)
    cc = str(cedula).strip()
    carpeta_servicio = _nombre_carpeta_servicio(servicio)
    patrones = [
        os.path.join(download_dir, carpeta_servicio, f"{cc}_{cod_serv}*.pdf"),
        os.path.join(download_dir, "*", f"{cc}_{cod_serv}*.pdf"),
    ]
    return any(len(glob.glob(p)) > 0 for p in patrones)


def _ya_existe_descarga_servicio(download_dir, cedula, servicio):
    cod_serv = _servicio_codigo(servicio)
    cc = str(cedula).strip()
    carpeta_servicio = _nombre_carpeta_servicio(servicio)
    patrones = [
        os.path.join(download_dir, carpeta_servicio, f"{cc}_{cod_serv}*.pdf"),
        os.path.join(download_dir, "*", f"{cc}_{cod_serv}*.pdf"),
    ]
    return any(len(glob.glob(p)) > 0 for p in patrones)


def _obtener_numero_factura_paciente(paciente):
    if not isinstance(paciente, dict):
        return None
    for clave in ("numero_factura", "numero de factura", "NUMERO DE FACTURA", "factura"):
        if clave in paciente and str(paciente.get(clave) or "").strip():
            return paciente.get(clave)
    return None


def _obtener_numero_ingreso_paciente(paciente):
    if not isinstance(paciente, dict):
        return None
    for clave in ("numero_ingreso", "numero de ingreso", "NUMERO DE INGRESO",
                  "NUMERO INGRESO", "nro_ingreso", "ingreso"):
        if clave in paciente and str(paciente.get(clave) or "").strip():
            valor = str(paciente.get(clave)).strip()
            if valor.endswith(".0"):
                valor = valor[:-2]
            if valor.lower() in ("nan", "none", ""):
                return None
            return valor
    return None


def run_bot_job(req: AgendaRequest):
    profesional = buscar_profesional_por_cc(req.cc)
    if profesional is None:
        raise ValueError(f"No se encontró profesional con cédula {req.cc}")
    fecha_str = req.fecha
    if fecha_str.lower() == "hoy":
        fecha_str = datetime.today().strftime("%d/%m/%Y")
    logger.info("Configuración de agenda actualizada para %s", profesional["nombre_mostrar"])
    bot = None
    runtime_config_path = build_agenda_runtime_config(
        sede=req.sede,
        nombre_profesional=profesional["nombre_config"],
        fecha_str=fecha_str,
        hora_inicio=req.hora_inicio,
        duracion_min=req.duracion_min,
        cantidad=req.cantidad,
        source="agenda_api",
    )
    agenda_configurada = False
    try:
        bot = _crear_bot_con_sesion(config_path=runtime_config_path)
        for intento in range(1, MAX_RECOVERY_ATTEMPTS + 1):
            try:
                _asegurar_bot_listo(bot, modulo="agenda", motivo=f"pre-chequeo agenda intento {intento}")
                if not agenda_configurada:
                    bot.configurar_agenda()
                    agenda_configurada = True
                bot.generar_agenda()
                logger.info("Bot finalizó correctamente")
                return
            except Exception as exc:
                if intento >= MAX_RECOVERY_ATTEMPTS or not _error_recuperable(exc):
                    raise
                logger.warning(
                    "Fallo recuperable en agenda. intento=%s/%s error=%s",
                    intento,
                    MAX_RECOVERY_ATTEMPTS,
                    exc,
                )
                bot = _reiniciar_bot(
                    bot,
                    config_path=runtime_config_path,
                    motivo=f"agenda intento {intento}: {exc}",
                )
                # Tras reabrir navegador y volver a loguear, la configuración de agenda
                # de la sesión web se pierde y debe reconstruirse antes de generar.
                agenda_configurada = False
    finally:
        if bot is not None:
            try:
                bot.cerrar()
            except Exception:
                logger.warning("Error cerrando bot", exc_info=True)
        cleanup_runtime_config(runtime_config_path)

def _parse_estrategia(estrategia_raw):
    """
    Interpreta la estrategia recibida desde Excel/UI.
    Permite combinar orden y tipo, por ejemplo:
    - RECIENTE
    - ANTIGUA
    - VALORACION
    - EVOLUCION
    - PRIMERA VEZ
    - ANTIGUA|EVOLUCION
    """
    txt = str(estrategia_raw or "").upper().strip()
    if not txt:
        return "RECIENTE", None

    orden = "RECIENTE"
    tipo = None

    tokens = [t.strip() for t in txt.replace("/", "|").replace(",", "|").split("|") if t.strip()]
    if not tokens:
        tokens = [txt]

    for t in tokens:
        if t in ("RECIENTE", "ANTIGUA"):
            orden = t
        elif t in ("VALORACION", "VAL"):
            tipo = "VALORACION"
        elif t in ("EVOLUCION", "EVO"):
            tipo = "EVOLUCION"
        elif t in ("PRIMERA VEZ", "PRIMERA_VEZ", "PRIMERA", "PRV"):
            tipo = "PRIMERA VEZ"

    # Si la celda trae solo tipo (sin RECIENTE/ANTIGUA), mantenemos orden por defecto RECIENTE.
    return orden, tipo

def run_hc_job(req: HCRequest, stop_event=None, progress_callback=None):
    """
    Ejecuta la descarga de historia clínica usando el bot.
    Soporta múltiples cédulas desde Excel o manual.
    Genera un informe final en Excel.
    """
    pacientes = []
    
    # 1. Prioridad: Lista desde Excel
    if req.pacientes_excel:
        # Si la plantilla tiene columna NUMERO DE FACTURA, pásala al diccionario de cada paciente
        for p in req.pacientes_excel:
            if isinstance(p, dict):
                # Si ya viene, no la toques
                pacientes.append(p)
            elif hasattr(p, '__dict__'):
                pacientes.append(p.__dict__)
            else:
                pacientes.append(dict(p))
        # Si es DataFrame, conviértelo
        if hasattr(req.pacientes_excel, 'columns') and 'NUMERO DE FACTURA' in req.pacientes_excel.columns:
            pacientes = [dict(row) for _, row in req.pacientes_excel.iterrows()]
    else:
        # 2. Fallback: Lista manual
        cedulas_raw = req.cedula.replace(",", "\n").split("\n")
        cedulas = [c.strip() for c in cedulas_raw if c.strip() and c.strip().isdigit()]
        for c in cedulas:
            # Soporte para múltiples servicios separados por coma
            servicios_raw = req.servicio.split(',') if req.servicio else [None]
            for serv in servicios_raw:
                s_limpio = serv.strip() if serv else None
                if not s_limpio and req.servicio: continue # Skip empty splits if original wasn't empty
                
                pacientes.append({
                    "cedula": c,
                    "servicio": s_limpio,
                    "estrategia": req.estrategia
                })
            
    if not pacientes:
        raise ValueError("No se proporcionaron cédulas válidas.")

    def emit_progress(completed, total, detail, current_item="", status="running"):
        if progress_callback:
            try:
                progress_callback(
                    {
                        "completed": completed,
                        "total": total,
                        "detail": detail,
                        "current_item": current_item,
                        "status": status,
                    }
                )
            except Exception:
                logger.warning("No fue posible publicar progreso HC", exc_info=True)

    logger.info(f"Iniciando descarga de HC para {len(pacientes)} pacientes.")
    emit_progress(0, len(pacientes), f"Preparando descarga de {len(pacientes)} registros...", status="running")

    # Marcar índice original para conservar orden en el informe final.
    for idx, p in enumerate(pacientes):
        p["_idx"] = idx

    # Lista para guardar el reporte detallado
    reporte_final = []

    # Crear carpeta de lote en el directorio interno del proyecto, salvo que el usuario indique otra ruta.
    base_descargas = _normalizar_ruta_descarga(req.ruta_descarga)
    os.makedirs(base_descargas, exist_ok=True)
    carpeta_lote = os.path.join(base_descargas, f"HC_MASIVA_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(carpeta_lote, exist_ok=True)
    logger.info(f"Carpeta de lote creada: {carpeta_lote}")


    # HC en paralelo: respeta cantidad_max del config y # real de credenciales.
    # Cada navegador usa una credencial distinta para evitar colisiones de sesion.
    credenciales_pool = _cargar_credenciales_hc()
    n_creds_validas = len([c for c in credenciales_pool if c])
    try:
        with open(Config.CONFIG_JSON_PATH, "r", encoding="utf-8") as _fcfg:
            _cfg_full = json.load(_fcfg)
        cantidad_max_cfg = int((_cfg_full.get("navegadores") or {}).get("cantidad_max", 1))
        navegador_tipo = str((_cfg_full.get("navegadores") or {}).get("tipo", "chrome")).strip().lower()
    except Exception:
        cantidad_max_cfg = 1
        navegador_tipo = "chrome"

    if navegador_tipo not in ("chrome", "edge"):
        navegador_tipo = "chrome"

    # ABSOLUTE TOPE: no abrir mas navegadores que credenciales validas, ni mas
    # que lo solicitado por el usuario, ni mas que pacientes.
    tope_logico = max(1, cantidad_max_cfg)
    if n_creds_validas > 0:
        tope_logico = min(tope_logico, n_creds_validas)
    tope_logico = min(tope_logico, len(pacientes))
    worker_count = max(1, tope_logico)

    # Construir el pool: cada hilo usa el navegador elegido por el usuario.
    # (Si el usuario eligio chrome, todos seran chrome con perfiles aislados;
    # si eligio edge, todos seran edge.)
    browser_pool = [navegador_tipo] * worker_count
    max_browsers = worker_count
    logger.info(
        "HC paralelismo: tipo=%s, solicitado=%d, credenciales=%d, pacientes=%d, "
        "workers efectivos=%d",
        navegador_tipo, cantidad_max_cfg, n_creds_validas, len(pacientes), worker_count,
    )

    total_pacientes = len(pacientes)
    progress_lock = threading.Lock()
    progress_state = {"completed": 0}

    lotes = [[] for _ in range(worker_count)]
    for p in pacientes:
        lotes[p["_idx"] % worker_count].append(p)

    def _procesar_lote(pacientes_lote, browser_preferido, idx_hilo, allow_browser_fallback=True):
        local_report = []
        bot = None
        browser_en_uso = browser_preferido
        cred_idx = idx_hilo % max(1, len(credenciales_pool))

        def cred_actual():
            return credenciales_pool[cred_idx] if credenciales_pool else None

        def rotar_credencial():
            nonlocal cred_idx
            if len(credenciales_pool) > 1:
                cred_idx = (cred_idx + 1) % len(credenciales_pool)
                logger.warning("Rotando credencial HC al usuario: %s", cred_actual().get("usuario", "N/A"))

        try:
            try:
                bot = _crear_bot_con_sesion(
                    config_path=Config.CONFIG_JSON_PATH,
                    download_dir=carpeta_lote,
                    browser_name=browser_en_uso,
                    credential_override=cred_actual(),
                )
            except Exception as exc_inicio:
                if allow_browser_fallback:
                    browser_en_uso = "chrome" if browser_en_uso == "edge" else "edge"
                    logger.warning(
                        "No fue posible iniciar navegador del hilo (%s). Se usa fallback %s.",
                        exc_inicio,
                        browser_en_uso.upper(),
                    )
                    bot = _crear_bot_con_sesion(
                        config_path=Config.CONFIG_JSON_PATH,
                        download_dir=carpeta_lote,
                        browser_name=browser_en_uso,
                        credential_override=cred_actual(),
                    )
                else:
                    raise

            for i_local, p in enumerate(pacientes_lote):
                if _detener_solicitado(stop_event):
                    logger.warning("[%s] Detención solicitada. Se cierra lote de forma segura.", browser_en_uso.upper())
                    break

                i_global = int(p.get("_idx", i_local))
                cedula = p["cedula"]
                if i_local > 0 and i_local % REINICIO_PREVENTIVO_CADA == 0:
                    logger.info(
                        "[MANTENIMIENTO] Reinicio preventivo hilo=%s tras %s CC.",
                        browser_en_uso,
                        i_local,
                    )
                    bot.mantenimiento_preventivo_hc(
                        motivo=f"cada {REINICIO_PREVENTIVO_CADA} CC procesadas ({browser_en_uso})"
                    )

                servicio = p.get("servicio") or req.servicio
                estrategia = p.get("estrategia") or req.estrategia
                orden_estrategia, tipo_hc_objetivo = _parse_estrategia(estrategia)
                numero_ingreso_pac = _obtener_numero_ingreso_paciente(p)
                _est_norm_pac = str(estrategia or "").upper().strip().replace("_", " ")
                es_rango_fechas = _est_norm_pac in ("RANGO FECHAS", "RANGO")

                f_ini_paciente = p.get("fecha_inicio")
                f_fin_paciente = p.get("fecha_fin")
                if f_ini_paciente:
                    f_ini_paciente = _normalizar_fecha_ddmmyyyy(f_ini_paciente)
                if f_fin_paciente:
                    f_fin_paciente = _normalizar_fecha_ddmmyyyy(f_fin_paciente)
                f_inicio_final = f_ini_paciente if f_ini_paciente is not None else req.fecha_inicio
                f_fin_final = f_fin_paciente if f_fin_paciente is not None else req.fecha_fin

                estado = "PENDIENTE"
                detalle = ""
                tipo_atencion = "N/A"

                try:
                    emit_progress(
                        progress_state["completed"],
                        total_pacientes,
                        f"Procesando {i_global + 1}/{total_pacientes}: CC {cedula} - {servicio or 'SIN SERVICIO'}",
                        current_item=f"CC {cedula} - {servicio or 'SIN SERVICIO'}",
                        status="running",
                    )
                    logger.info(
                        "[%s] Procesando %s/%s: CC=%s, Serv=%s, Fechas=%s-%s",
                        browser_en_uso.upper(),
                        i_global + 1,
                        len(pacientes),
                        cedula,
                        servicio,
                        f_inicio_final,
                        f_fin_final,
                    )

                    for intento_pre in range(1, MAX_RECOVERY_ATTEMPTS + 1):
                        try:
                            _asegurar_bot_listo(bot, modulo="hc", motivo=f"pre-chequeo HC CC={cedula}")
                            break
                        except Exception as exc:
                            es_transitorio_pre = _error_recuperable(exc) or _es_resultado_transitorio_hc(exc)
                            if intento_pre >= MAX_RECOVERY_ATTEMPTS or not es_transitorio_pre:
                                raise
                            bot = _recuperar_o_reiniciar_bot(
                                bot,
                                config_path=Config.CONFIG_JSON_PATH,
                                download_dir=carpeta_lote,
                                motivo=f"pre-chequeo HC CC={cedula} intento {intento_pre}: {exc}",
                                browser_name=browser_en_uso,
                                credential_override=cred_actual(),
                            )

                    ya_existe = False
                    # En modo RANGO FECHAS o cuando se solicita un ingreso especifico,
                    # NO saltamos por cache: pueden existir mas HCs por descargar.
                    if not es_rango_fechas and not numero_ingreso_pac:
                        if tipo_hc_objetivo:
                            ya_existe = _ya_existe_descarga_tipo(bot.download_dir, cedula, servicio, tipo_hc_objetivo)
                        else:
                            ya_existe = _ya_existe_descarga_servicio(bot.download_dir, cedula, servicio)

                    if ya_existe:
                        estado = "TIENE HC"
                        tipo_atencion = tipo_hc_objetivo or "N/A"
                        detalle = "Tiene HC y ya estaba descargada para esta cédula/servicio"
                    else:
                        exito = False
                        info = ""
                        for intento_hc in range(1, MAX_RECOVERY_ATTEMPTS + 1):
                            if _detener_solicitado(stop_event):
                                info = "Detenido por usuario"
                                break
                            try:
                                exito, info = bot.descargar_historia_clinica(
                                    cedula=cedula,
                                    fecha_inicio=f_inicio_final,
                                    fecha_fin=f_fin_final,
                                    servicio=servicio,
                                    estrategia=("RANGO FECHAS" if es_rango_fechas else orden_estrategia),
                                    tipo_hc_objetivo=tipo_hc_objetivo,
                                    numero_factura=_obtener_numero_factura_paciente(p),
                                    numero_ingreso=numero_ingreso_pac,
                                )
                                if not exito and _es_resultado_sin_hc(info):
                                    # "Sin resultados" se considera resultado funcional de negocio.
                                    break
                                if not exito and _es_resultado_transitorio_hc(info):
                                    raise RuntimeError(f"Resultado transitorio en HC: {info}")
                                break
                            except Exception as exc:
                                es_transitorio = _es_resultado_transitorio_hc(exc) or _error_recuperable(exc)
                                if intento_hc >= MAX_RECOVERY_ATTEMPTS or not es_transitorio:
                                    raise
                                # Rotar usuario al recuperar para evitar colisión de sesión.
                                rotar_credencial()
                                bot = _recuperar_o_reiniciar_bot(
                                    bot,
                                    config_path=Config.CONFIG_JSON_PATH,
                                    download_dir=carpeta_lote,
                                    motivo=f"HC CC={cedula} intento {intento_hc}: {exc}",
                                    browser_name=browser_en_uso,
                                    credential_override=cred_actual(),
                                )
                                _asegurar_bot_listo(bot, modulo="hc", motivo=f"post-reinicio HC CC={cedula}")

                        if exito:
                            estado = "TIENE HC"
                            detalle = "Tiene HC y se descargó correctamente"
                            tipo_atencion = info
                        else:
                            if _es_resultado_sin_hc(info):
                                estado = "NO TIENE HC"
                                detalle = (
                                    f"No tiene HC en las fechas seleccionadas "
                                    f"({f_inicio_final or 'SIN FECHA INICIO'} a {f_fin_final or 'SIN FECHA FIN'})"
                                )
                            else:
                                estado = "FALLO"
                                detalle = info if info else "No se pudo descargar (ver logs)"

                except Exception as e:
                    logger.error("Error procesando cédula %s en %s: %s", cedula, browser_en_uso, e)
                    estado = "ERROR"
                    detalle = str(e)

                # RED DE SEGURIDAD: tras cada paciente, mover cualquier PDF que
                # haya quedado suelto en la raiz de download_dir a la carpeta
                # del servicio que se acaba de procesar.
                try:
                    if bot is not None and hasattr(bot, "barrer_pdfs_huerfanos"):
                        bot.barrer_pdfs_huerfanos(cedula=cedula, servicio=servicio)
                except Exception as ex_barrido:
                    logger.warning("Barrido post-paciente fallo CC=%s: %s", cedula, ex_barrido)

                local_report.append({
                    "_idx": i_global,
                    "Cedula": cedula,
                    "Servicio": servicio,
                    "Estrategia": estrategia,
                    "Fecha Inicio": f_inicio_final,
                    "Fecha Fin": f_fin_final,
                    "Tipo Atencion": tipo_atencion,
                    "Estado": estado,
                    "Detalle": detalle,
                    "FechaHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Navegador": browser_en_uso.upper(),
                })

                with progress_lock:
                    progress_state["completed"] += 1
                    emit_progress(
                        progress_state["completed"],
                        total_pacientes,
                        f"Avance {progress_state['completed']}/{total_pacientes}. Último registro: CC {cedula} - {estado}",
                        current_item=f"CC {cedula} - {servicio or 'SIN SERVICIO'}",
                        status="running",
                    )

        except Exception as error_lote:
            logger.error("Hilo %s falló al iniciar/procesar: %s", browser_preferido, error_lote)
            for p in pacientes_lote:
                local_report.append({
                    "_idx": int(p.get("_idx", 0)),
                    "Cedula": p.get("cedula"),
                    "Servicio": p.get("servicio") or req.servicio,
                    "Estrategia": p.get("estrategia") or req.estrategia,
                    "Fecha Inicio": p.get("fecha_inicio") if p.get("fecha_inicio") is not None else req.fecha_inicio,
                    "Fecha Fin": p.get("fecha_fin") if p.get("fecha_fin") is not None else req.fecha_fin,
                    "Tipo Atencion": "N/A",
                    "Estado": "ERROR",
                    "Detalle": f"No fue posible ejecutar el hilo en navegador {browser_preferido}: {error_lote}",
                    "FechaHora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Navegador": browser_preferido.upper(),
                })
        finally:
            if bot is not None:
                # Barrido FINAL del lote: cualquier PDF suelto que quede en
                # la raiz se va a _SIN_CLASIFICAR antes de cerrar el navegador.
                try:
                    if hasattr(bot, "barrer_pdfs_huerfanos"):
                        bot.barrer_pdfs_huerfanos(cedula=None, servicio=None)
                except Exception:
                    logger.warning("Barrido final de lote fallo en %s", browser_preferido, exc_info=True)
                try:
                    bot.cerrar()
                except Exception:
                    logger.warning("Error cerrando bot de hilo %s", browser_preferido, exc_info=True)
        return local_report

    if worker_count == 1:
        reporte_final.extend(_procesar_lote(lotes[0], browser_pool[0], 0))
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(_procesar_lote, lotes[idx], browser_pool[idx], idx)
                for idx in range(worker_count)
                if lotes[idx]
            ]
            for fut in as_completed(futures):
                reporte_final.extend(fut.result())

    reporte_final.sort(key=lambda x: x.get("_idx", 0))
    emit_progress(len(reporte_final), total_pacientes, f"Generando informe final de {len(reporte_final)} registros...", status="running")

    # Generar Informe Excel
    ruta_reporte = None
    try:
        df_reporte = pd.DataFrame([{k: v for k, v in r.items() if k != "_idx"} for r in reporte_final])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_reporte = f"Informe_Descargas_{timestamp}.xlsx"
        ruta_reporte = os.path.join(carpeta_lote, nombre_reporte)
        df_reporte.to_excel(ruta_reporte, index=False)
        logger.info(f"Informe generado en: {ruta_reporte}")
    except Exception as e_rep:
        logger.error(f"No se pudo generar el informe Excel: {e_rep}")

    # Resumen para logs
    con_hc = len([r for r in reporte_final if r["Estado"] == "TIENE HC"])
    sin_hc = len([r for r in reporte_final if r["Estado"] == "NO TIENE HC"])
    fallos = len([r for r in reporte_final if r["Estado"] in ("FALLO", "ERROR")])
    msg = (
        f"Proceso finalizado. Con HC: {con_hc}, Sin HC: {sin_hc}, "
        f"Fallos: {fallos}. Informe guardado."
    )
    logger.info(msg)

    detenido = _detener_solicitado(stop_event)
    if detenido:
        logger.warning("Proceso HC detenido por usuario. Informe parcial disponible en: %s", ruta_reporte)

    # Solo se considera error global cuando no hubo ningún resultado funcional
    # y sí hubo fallos reales de ejecución.
    if (not detenido) and con_hc == 0 and sin_hc == 0 and fallos > 0:
        raise Exception(f"Todas las descargas fallaron ({len(pacientes)}). Ver informe.")

    return {
        "con_hc": con_hc,
        "sin_hc": sin_hc,
        "fallos": fallos,
        "detenido": detenido,
        "ruta_informe": ruta_reporte,
    }
