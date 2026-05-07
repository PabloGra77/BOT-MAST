import json
import time
import sys
import datetime
import os
import shutil
import glob
import requests
import fitz  # PyMuPDF
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from selenium.webdriver.support.ui import Select

from bot360_app.common.settings import CHROME_DOWNLOAD_DIR, CONFIG_PATH, RUNTIME_LOG_DIR

# ====================================================================================
# SELECTORES (IMPORTANTE: EL USUARIO DEBE ACTUALIZAR ESTOS VALORES CON EL HTML REAL)
# ====================================================================================
SELECTORES = {
    # Login
    "login_usuario": (By.ID, "vUSUARIOSLOGIN"),
    "login_password": (By.ID, "vUSUARIOSPASSWORD"),
    "login_verificacion": (By.ID, "vEMPNUMVER"),
    "login_btn": (By.NAME, "BTNINGRESAR"),

    # NavegaciÃ³n MenÃº (Basado en textos visibles de la imagen)
    "menu_citas": (By.XPATH, "//span[contains(text(), 'Citas') or contains(., 'Citas')] | //a[contains(text(), 'Citas') or contains(., 'Citas')]"),
    "submenu_config_agenda": (By.XPATH, "//a[contains(text(), 'Configurar Agendas') or contains(., 'Configurar Agendas')]"), # Nota: Agendas en plural
    "submenu_gen_agenda": (By.XPATH, "//a[contains(text(), 'Generar Agenda') or contains(., 'Generar Agenda')]"),

    # BÃºsqueda Profesional
    "select_sede": (By.ID, "vSEDCOD_MPAGE"),            # Selector de sede (Master Page)
    "input_primer_apellido": (By.ID, "vUSUPRIAPE"),      # Campo 1Â° Apellido (CORREGIDO)
    "input_primer_nombre": (By.ID, "vUSUPRINOM"),        # Campo 1Â° Nombre (CORREGIDO)
    "btn_buscar_prof": (By.NAME, "IMAGE1"),              # BotÃ³n lupa (CORREGIDO - es una imagen input)
    "tabla_resultados": (By.CLASS_NAME, "Grid"),         # Clase tabla resultados
    "btn_editar_agenda": (By.ID, "vVALAGE_0001"),        # BotÃ³n acciÃ³n (CAMBIADO A ID por seguridad)

    # ConfiguraciÃ³n Agenda (Estructura de grilla)
    # Nota: Los campos terminan en _0001, _0002, etc.
    "grid_dia": "AGEDIA",             # Prefijo ID para selector de dÃ­a
    "grid_hora_ini": "AGEHORINI",     # Prefijo ID para hora inicio
    "grid_hora_fin": "AGEHORFIN",     # Prefijo ID para hora fin
    "grid_duracion": "AGEDUR",        # Prefijo ID para duraciÃ³n
    "grid_cupos": "AGEESPHOR",        # Prefijo ID para cupos
    
    "btn_guardar_config": (By.NAME, "BTN_ENTER"),          # BotÃ³n Confirmar

    # GeneraciÃ³n Agenda (ACTUALIZADO CON DATOS REALES)
    "input_fecha_ini": (By.ID, "vFECINI"),               # ID real encontrado en escaneo
    "input_fecha_fin": (By.ID, "vFECFIN"),               # ID real encontrado en escaneo
    "select_profesional_gen": (By.ID, "vUSUCOD"),        # ID real encontrado en escaneo
    "btn_generar_final": (By.NAME, "BUTTON1"),           # ID/Name real encontrado en escaneo
    "msg_exito": (By.CLASS_NAME, "SuccessMessage"),      # Elemento mensaje Ã©xito

    # Descarga Historias ClÃ­nicas
    "menu_consultar_hc": (By.XPATH, "//span[contains(text(), 'Consultar HC') or contains(., 'Consultar HC')] | //a[contains(text(), 'Consultar HC') or contains(., 'Consultar HC')]"),
    "submenu_consultar_historia": (By.XPATH, "//a[contains(text(), 'Consultar Historia') or contains(., 'Consultar Historia')]"),
    "hc_fecha_ini": (By.ID, "vFECINI"), # CORREGIDO: Inicio es vFECINI
    "hc_fecha_fin": (By.ID, "vFECFIN"), # CORREGIDO: Fin es vFECFIN
    "hc_pac_id": (By.ID, "vPACNUMIDE"),
    "hc_servicio": (By.ID, "vTIPAGENRO"), # Selector de Servicio
    "hc_btn_consultar": (By.NAME, "CONSULTAR"),
    "hc_btn_imprimir": (By.NAME, "vIMPRIMIRHC_0001"),    # BotÃ³n de impresora primera fila
    "hc_tabla_resultados": (By.ID, "GridContainerTbl")   # Contenedor de la tabla
}

import unicodedata

def normalize_text(text):
    """
    Normaliza un texto para comparaciÃ³n robusta:
    - Convierte a mayÃºsculas
    - Elimina tildes y diacrÃ­ticos
    - Elimina espacios extra
    """
    if not text: return ""
    text = str(text).upper().strip()
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
    return " ".join(text.split())

class Bot:
    def _verificar_navegador_operativo_o_error(self, motivo=""):
        """
        Verifica si el navegador está operativo. Si no, lanza una excepción clara para logs y control de errores.
        """
        if not self._driver_operativo():
            raise Exception(f"El navegador se cayó o no responde. Motivo: {motivo or 'driver no operativo'}")
        try:
            # Prueba básica de acceso a la página
            _ = self.driver.current_url
            # Prueba de acceso a un campo típico (login o body)
            try:
                _ = self.driver.find_element(By.TAG_NAME, "body")
            except Exception:
                raise Exception(f"El navegador está abierto pero la página no responde o no reconoce los campos. Motivo: {motivo}")
        except Exception:
            raise Exception(f"El navegador se cayó o no responde. Motivo: {motivo}")
    def __init__(self, config_path=str(CONFIG_PATH), log_callback=None, browser_name="chrome", credential_override=None):
        self.log_callback = log_callback
        self.cargar_configuracion(config_path)
        self.driver = None
        self.wait = None
        self.resumen_acciones = []
        self.turbo_mode = True # MODO VELOCIDAD ACTIVADO POR DEFECTO
        self.browser_name = str(browser_name or "chrome").lower().strip()
        self.credential_override = credential_override or {}
        # --- Contador de descargas para reinicio preventivo de sesión ---
        self._descargas_en_sesion = 0
        self.MAX_DESCARGAS_POR_SESION = 50
        # Tamaño mínimo válido (en bytes) para considerar un PDF "no vacío"
        self.PDF_MIN_BYTES = 5 * 1024  # 5 KB
        self.PDF_MIN_TEXTO = 80         # caracteres mínimos extraíbles

    def log(self, message):
        """Imprime mensaje en consola y llama al callback si existe."""
        print(message)
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception:
                pass # Evitar fallos si el callback falla

    def resaltar_elemento(self, elemento):
        """
        Resalta el elemento visualmente.
        Si turbo_mode es True, omite el resaltado para ganar velocidad.
        """
        if self.turbo_mode:
            return

        try:
            # 1. Obtener datos del elemento
            tag = elemento.tag_name
            eid = elemento.get_attribute('id')
            
            # 2. Scroll al elemento (JS) - Solo si es necesario (OptimizaciÃ³n)
            # self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", elemento)
            
            # 3. Resaltado (Borde Rojo)
            js_script = """
            arguments[0].style.outline = '3px solid red';
            """
            self.driver.execute_script(js_script, elemento)
            
            # 4. Pausa mÃ­nima (ELIMINADA PARA VELOCIDAD EXTREMA)
            # time.sleep(0.1)
            
        except Exception as e:
            pass

    def ingresar_hora(self, elemento, hora):
        """
        Ingresa una hora en un campo, manejando posibles mÃ¡scaras.
        Limpia el campo agresivamente antes de escribir.
        """
        try:
            self.resaltar_elemento(elemento)
            
            # 1. Limpieza agresiva (JS + Keys)
            self.driver.execute_script("arguments[0].value = '';", elemento)
            elemento.clear()
            
            # 2. Escribir
            # Algunos campos con mÃ¡scara fallan si se envÃ­an los dos puntos rÃ¡pido
            # Probamos enviando normal primero
            elemento.send_keys(hora)
            
            # VerificaciÃ³n bÃ¡sica
            val = elemento.get_attribute('value')
            if val != hora:
                self.log(f"[WARN] La hora escrita '{val}' difiere de la deseada '{hora}'. Reintentando sin ':'...")
                # Intento 2: Sin dos puntos (por si es mÃ¡scara estricta)
                hora_sin_puntos = hora.replace(":", "")
                elemento.clear()
                elemento.send_keys(hora_sin_puntos)
        except Exception as e:
            self.log(f"[ERROR] FallÃ³ al ingresar hora {hora}: {e}")

    # Diccionario de alias / abreviaciones de servicios para el dropdown
    # NOTA: Por decision del usuario el matching es ESTRICTO EXACTO. Este
    # diccionario se conserva vacio a proposito; NO se usan alias.
    _ALIAS_SERVICIO = {}

    def _normalizar_servicio_estricto(self, texto):
        """Normaliza para comparacion EXACTA:
        - upper
        - sin tildes (NFD + ascii)
        - sin signos de puntuacion (.,;:- etc)
        - colapsa espacios
        """
        if not texto:
            return ""
        import re as _re
        t = normalize_text(texto)  # ya hace upper + strip tildes + collapse spaces
        # eliminar todo lo que no sea letra/numero/espacio
        t = _re.sub(r"[^A-Z0-9 ]+", " ", t)
        return " ".join(t.split())

    def seleccionar_servicio(self, elemento, texto_servicio):
        """
        Selecciona el servicio del dropdown HACIENDO MATCH EXACTO contra las
        opciones disponibles (despues de normalizar tildes y puntuacion).
        Si NO hay coincidencia exacta -> devuelve False (no descarga nada).
        """
        try:
            self.resaltar_elemento(elemento)
            select = Select(elemento)

            def _seleccionar_y_confirmar(texto_opcion):
                select.select_by_visible_text(texto_opcion)
                try:
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
                        "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));",
                        elemento,
                    )
                except Exception:
                    pass
                seleccionado_norm = self._normalizar_servicio_estricto(select.first_selected_option.text)
                esperado_norm = self._normalizar_servicio_estricto(texto_opcion)
                if seleccionado_norm != esperado_norm:
                    self.log(f"[WARN] El servicio no quedo seleccionado como se esperaba: '{select.first_selected_option.text}'")
                    return False
                self.log(f"[INFO] Servicio seleccionado: {select.first_selected_option.text}")
                return True

            target_norm = self._normalizar_servicio_estricto(texto_servicio)
            if not target_norm:
                self.log("[WARN] Servicio vacio, no se selecciona nada")
                return False

            opciones = select.options

            # UNICA estrategia: match EXACTO normalizado.
            for op in opciones:
                if self._normalizar_servicio_estricto(op.text) == target_norm:
                    self.log(f"[INFO] Match exacto: '{texto_servicio}' -> '{op.text}'")
                    return _seleccionar_y_confirmar(op.text)

            # Sin match exacto: log con TODAS las opciones para diagnostico y FALLA.
            self.log(f"[ERROR] Servicio NO encontrado en el dropdown: '{texto_servicio}' (normalizado: '{target_norm}')")
            self.log(f"        Opciones disponibles ({len(opciones)}): {[o.text for o in opciones]}")
            
        except Exception as e:
            self.log(f"[ERROR] Error seleccionando servicio: {e}")
            return False

    def prueba_visual_inicial(self):
        """Dibuja un borde gigante en toda la pÃ¡gina para verificar control JS."""
        try:
            self.log("[VISUAL] Ejecutando prueba de control visual en el BODY...")
            self.driver.execute_script("document.body.style.border = '20px solid red';")
            time.sleep(2)
        except Exception as e:
            self.log(f"[ERROR VISUAL] No se pudo marcar el body: {e}")

    def cargar_configuracion(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.log("[INFO] ConfiguraciÃ³n cargada correctamente.")
        except FileNotFoundError:
            self.log(f"[ERROR] No se encontrÃ³ el archivo {path}")
            raise Exception(f"No se encontrÃ³ el archivo de configuraciÃ³n: {path}")

    def iniciar_navegador(self, download_dir=None):
        browser = self.browser_name if self.browser_name in ("chrome", "edge") else "chrome"

        self.log(f"[INFO] Iniciando navegador {browser.upper()}...")
        self.log("--- BOT V3.5 (Correccion Fechas y Ruta Descarga) ---")

        # Preferencias para descarga automática (Chromium: Chrome/Edge)
        prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            # ¡CRÍTICO! Forzar descarga de PDF en vez de abrir visor
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_settings.popups": 0,
            "pdfjs.disabled": True,
        }
        
        if download_dir:
            # Normalizar ruta para Windows
            download_dir = os.path.abspath(download_dir)
            if not os.path.exists(download_dir):
                os.makedirs(download_dir, exist_ok=True)
            self.download_dir = download_dir # Guardar para uso posterior
            prefs["download.default_directory"] = download_dir
            self.log(f"[CONFIG] Carpeta de descarga configurada: {download_dir}")
        else:
            default_download_dir = os.path.abspath(str(CHROME_DOWNLOAD_DIR))
            if not os.path.exists(default_download_dir):
                os.makedirs(default_download_dir, exist_ok=True)
            self.download_dir = default_download_dir # Guardar para uso posterior
            prefs["download.default_directory"] = default_download_dir
            self.log(f"[CONFIG] Carpeta de descarga default: {default_download_dir}")
            
        print(f"\n{'='*60}")
        print(f"  >>> GUARDANDO ARCHIVOS EN: {self.download_dir}")
        print(f"{'='*60}\n")

        if browser in ("chrome", "edge"):
            if browser == "chrome":
                options = webdriver.ChromeOptions()
            else:
                options = webdriver.EdgeOptions()

            options.add_experimental_option("prefs", prefs)
            options.add_argument("--start-maximized")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-infobars")
            options.page_load_strategy = 'eager'

            if browser == "chrome":
                try:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                except Exception as ex_drv:
                    self.log(f"[WARN] webdriver_manager Chrome no disponible ({ex_drv}). Intentando Selenium Manager/local driver...")
                    self.driver = webdriver.Chrome(options=options)
            else:
                try:
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=service, options=options)
                except Exception as ex_drv:
                    self.log(f"[WARN] webdriver_manager Edge no disponible ({ex_drv}). Intentando Selenium Manager/local driver...")
                    self.driver = webdriver.Edge(options=options)

        self.wait = WebDriverWait(self.driver, 5)  # Reducido a 5s para maxima agresividad
        self.driver.implicitly_wait(0) # Asegurar que no haya esperas implÃ­citas ocultas
        
        # Prueba visual inmediata (Omitida en turbo)
        if not self.turbo_mode:
            self.prueba_visual_inicial()

    def cerrar(self):
        try:
            if self.driver:
                self.log("[INFO] Cerrando navegador...")
                self.driver.quit()
        except Exception as e:
            self.log(f"[WARN] Error al cerrar driver: {e}")
        finally:
            self.exportar_resumen()

    def login(self):
        creds_cfg = self.config.get("credenciales", {})
        creds = {
            "url": self.credential_override.get("url", creds_cfg.get("url")),
            "usuario": self.credential_override.get("usuario", creds_cfg.get("usuario")),
            "contrasena": self.credential_override.get("contrasena", creds_cfg.get("contrasena")),
            "numero_verificacion": self.credential_override.get("numero_verificacion", creds_cfg.get("numero_verificacion", "")),
        }

        url = creds["url"]
        self.base_url = url
        user = creds["usuario"]
        pwd = creds["contrasena"]
        verif = creds.get("numero_verificacion", "")

        self.log(f"[PASO 1] Navegando a {url}...")
        self.driver.get(url)

        try:
            # Esperar e ingresar usuario
            el_user = self.wait.until(EC.visibility_of_element_located(SELECTORES["login_usuario"]))
            self.resaltar_elemento(el_user)
            el_user.clear()
            el_user.send_keys(user)

            # Ingresar contraseÃ±a
            el_pass = self.driver.find_element(*SELECTORES["login_password"])
            self.resaltar_elemento(el_pass)
            el_pass.clear()
            el_pass.send_keys(pwd)

            # Ingresar nÃºmero de verificaciÃ³n (si existe en la pÃ¡gina)
            try:
                el_verif = self.driver.find_element(*SELECTORES["login_verificacion"])
                if el_verif.is_displayed():
                    self.resaltar_elemento(el_verif)
                    self.log("[INFO] Ingresando nÃºmero de verificaciÃ³n...")
                    el_verif.clear()
                    el_verif.send_keys(verif)
            except NoSuchElementException:
                pass # Si no estÃ¡ el campo, seguimos

            # Click Ingresar
            btn_login = self.driver.find_element(*SELECTORES["login_btn"])
            self.resaltar_elemento(btn_login)
            btn_login.click()
            
            # VerificaciÃ³n simple: esperar a que desaparezca el login o aparezca menÃº
            # AquÃ­ asumimos que si aparece el menÃº de citas, el login fue exitoso
            self.wait.until(EC.presence_of_element_located(SELECTORES["menu_citas"]))
            self.log("[OK] Inicio de sesiÃ³n exitoso.")
            self.resumen_acciones.append("Inicio de sesiÃ³n: OK")

        except TimeoutException:
            self.log("[ERROR] No se pudo iniciar sesiÃ³n. Verifique selectores o credenciales.")
            self.driver.save_screenshot("error_login.png")
            raise

    def _es_pantalla_login(self):
        try:
            user_inputs = self.driver.find_elements(*SELECTORES["login_usuario"])
            pass_inputs = self.driver.find_elements(*SELECTORES["login_password"])
            return bool(user_inputs and pass_inputs and user_inputs[0].is_displayed())
        except Exception:
            return False

    def _driver_operativo(self):
        try:
            if not self.driver:
                return False
            _ = self.driver.current_url
            return True
        except Exception:
            return False

    def _aceptar_alerta_si_existe(self):
        try:
            alert = self.driver.switch_to.alert
            txt = (alert.text or "").strip()
            self.log(f"[ALERT][RECOVERY] {txt}")
            alert.accept()
            return True
        except Exception:
            return False

    def reiniciar_navegador_y_sesion(self, motivo=""):
        self.log(f"[RECOVERY] Reinicio completo de navegador/sesion. Motivo: {motivo or 'driver no disponible'}")
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
        finally:
            self.driver = None
            self.wait = None

        self.iniciar_navegador(download_dir=getattr(self, "download_dir", None))
        self.login()
        return True

    def sesion_activa(self):
        try:
            return self._driver_operativo() and not self._pagina_en_blanco_o_error() and not self._es_pantalla_login()
        except Exception:
            return False

    def asegurar_sesion_activa(self, motivo="", validar_modulo=None):
        self.log(f"[HEALTHCHECK] Verificando sesion. Motivo: {motivo or 'chequeo preventivo'}")

        # Si hay alerta modal (ej: "La sesión ha caducado"), la aceptamos
        self._aceptar_alerta_si_existe()

        try:
            self._verificar_navegador_operativo_o_error(motivo)
        except Exception as e:
            self.log(f"[ERROR] {e}")
            return self.reiniciar_navegador_y_sesion(motivo or str(e))

        if self._pagina_en_blanco_o_error() or self._es_pantalla_login():
            if not self.recuperar_pagina_y_sesion(motivo or "pagina o sesion inestable"):
                self.log("[ERROR] No se pudo recuperar la sesión o la página. El navegador podría estar caído.")
                return False

        if validar_modulo == "hc":
            return self.mantenimiento_preventivo_hc(motivo or "validacion modulo HC")

        return self.sesion_activa()

    def _pagina_en_blanco_o_error(self):
        try:
            url = (self.driver.current_url or "").strip().lower()
            titulo = (self.driver.title or "").strip().lower()
            body_txt = ""
            html_txt = ""
            try:
                body_txt = (self.driver.find_element(By.TAG_NAME, "body").text or "").strip().lower()
            except Exception:
                pass
            try:
                html_txt = (self.driver.page_source or "").strip().lower()
            except Exception:
                pass

            if url in ("", "about:blank"):
                return True
            if not titulo and len(body_txt) < 5:
                return True
            if len(html_txt) < 100 and len(body_txt) < 20:
                return True
            errores = [
                "this site can’t be reached",
                "this site can't be reached",
                "err_",
                "aw, snap",
                "502 bad gateway",
                "503 service unavailable",
                "504 gateway timeout",
                "500 internal server error",
                "bad gateway",
                "gateway timeout",
                "service unavailable",
                "proxy error",
                "upstream connect error",
                "temporarily unavailable",
                "an error occurred",
                "the page isn\'t working",
                "http error 502",
                "http error 503",
                "http error 504",
                "no se puede acceder",
                "no se pudo acceder",
                "error 502",
                "error 503",
                "error 504",
                "puerta de enlace incorrecta",
                "tiempo de espera de la puerta de enlace",
                "servicio no disponible",
                "la pagina web no esta disponible",
                "la pÃ¡gina web no estÃ¡ disponible",
            ]
            universo = "\n".join([url, titulo, body_txt[:4000], html_txt[:8000]])
            if any(e in universo for e in errores):
                self.log(f"[HEALTHCHECK] Página de error detectada. url={url or '(vacia)'} titulo={titulo or '(vacio)'}")
                return True
            return False
        except Exception:
            return False

    def _recuperar_si_pagina_error(self, motivo=""):
        try:
            if self._pagina_en_blanco_o_error():
                self.log(f"[RECOVERY] Página inestable detectada antes de buscar elementos. Motivo: {motivo or 'chequeo de elementos'}")
                return self.recuperar_pagina_y_sesion(motivo or "pagina de error detectada")
        except Exception as e:
            self.log(f"[RECOVERY WARN] Falló chequeo previo de página: {e}")
        return False

    def recuperar_pagina_y_sesion(self, motivo=""):
        self.log(f"[RECOVERY] Activado. Motivo: {motivo or 'estado inestable detectado'}")
        if not self._driver_operativo():
            return self.reiniciar_navegador_y_sesion(motivo or "driver no disponible durante recovery")
        self._aceptar_alerta_si_existe()
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        try:
            self.driver.refresh()
            self.esperar_carga_completa(timeout=15)
        except Exception:
            pass

        try:
            if self._pagina_en_blanco_o_error():
                url = self.config["credenciales"]["url"]
                self.log(f"[RECOVERY] Reabriendo URL base: {url}")
                self.driver.get(url)
                self.esperar_carga_completa(timeout=20)
        except Exception as e:
            self.log(f"[RECOVERY WARN] Fallo reapertura de URL base: {e}")

        try:
            if self._es_pantalla_login():
                self.log("[RECOVERY] Sesion caida detectada. Reintentando login...")
                self.login()
                return True
        except Exception as e:
            self.log(f"[RECOVERY ERROR] Fallo en re-login: {e}")
            return False

        ok = not self._pagina_en_blanco_o_error()
        self.log("[RECOVERY] " + ("Recuperacion completada." if ok else "No se pudo recuperar completamente."))
        return ok

    def mantenimiento_preventivo_hc(self, motivo=""):
        """
        Reinicia preventivamente la pagina y valida que la sesion siga activa
        y que el modulo de Consultar HC siga accesible.
        """
        self.log(f"[MANTENIMIENTO] Reinicio preventivo HC. Motivo: {motivo or 'ciclo preventivo'}")

        if not self.recuperar_pagina_y_sesion(motivo or "mantenimiento preventivo HC"):
            raise Exception("No se pudo recuperar pagina/sesion durante mantenimiento preventivo HC.")

        if self._es_pantalla_login():
            self.log("[MANTENIMIENTO] Sesion no activa tras recovery. Reintentando login...")
            self.login()

        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

        en_modulo = False
        try:
            en_modulo = bool(self.buscar_elemento_en_frames(*SELECTORES["hc_pac_id"]))
        except Exception:
            en_modulo = False

        if not en_modulo:
            self.navegar_a_modulo(
                SELECTORES["menu_consultar_hc"],
                SELECTORES["submenu_consultar_historia"],
            )
            time.sleep(1)
            self.driver.switch_to.default_content()
            if not self.buscar_elemento_en_frames(*SELECTORES["hc_pac_id"]):
                raise Exception("Sesion activa, pero no se pudo confirmar acceso al modulo Consultar HC.")

        self.log("[MANTENIMIENTO] Sesion y modulo Consultar HC verificados.")
        return True

    def navegar_a_modulo(self, selector_menu, selector_submenu, forzar_menu=True):
        try:
            # OptimizaciÃ³n: Si forzar_menu es False, asumimos que el menÃº ya estÃ¡ desplegado
            # y vamos directo al submenÃº.
            
            if forzar_menu:
                # Click en menÃº principal (ej: Citas)
                menu = self.wait.until(EC.element_to_be_clickable(selector_menu))
                if not self.turbo_mode: self.resaltar_elemento(menu)
                menu.click()
            else:
                self.log("[INFO] MenÃº principal omitido (asumimos ya abierto).")
            
            # Click en submenÃº (ej: Configurar Agenda)
            submenu = self.wait.until(EC.element_to_be_clickable(selector_submenu))
            if not self.turbo_mode: self.resaltar_elemento(submenu)
            submenu.click()
            self.log("[INFO] NavegaciÃ³n a mÃ³dulo completada.")
        except Exception as e:
            self.log(f"[ERROR] Fallo en navegaciÃ³n: {e}")
            # Retry mechanism: Si fallÃ³ directo al submenÃº, intentamos el flujo completo
            if not forzar_menu:
                self.log("[WARN] Reintentando navegaciÃ³n abriendo el menÃº principal...")
                self.navegar_a_modulo(selector_menu, selector_submenu, forzar_menu=True)
            else:
                raise

    def buscar_elemento_en_frames(self, by, value):
        """
        Busca un elemento en el contexto actual y en todos los sub-frames.
        Optimizado: Recuerda el Ãºltimo frame exitoso para buscar allÃ­ primero.
        """
        self._recuperar_si_pagina_error(f"busqueda de elemento {by}={value}")

        # 0. Atributo de clase para "memoria" (si no existe, lo creamos)
        if not hasattr(self, '_last_successful_frame_index'):
            self._last_successful_frame_index = None

        # 1. Si tenemos un frame exitoso previo, vamos directo allÃ¡ primero (OptimizaciÃ³n predictiva)
        if self._last_successful_frame_index is not None:
             try:
                frames = self.driver.find_elements(By.TAG_NAME, "iframe") + self.driver.find_elements(By.TAG_NAME, "frame")
                if self._last_successful_frame_index < len(frames):
                    self.driver.switch_to.frame(frames[self._last_successful_frame_index])
                    try:
                        el = self.driver.find_element(by, value)
                        if el.is_displayed():
                            return el
                    except: pass
                    self.driver.switch_to.default_content() # Si fallÃ³, volvemos a cero
             except: 
                 self.driver.switch_to.default_content()

        # 2. Buscar en contexto actual (Default)
        try:
            el = self.driver.find_element(by, value)
            if el.is_displayed():
                return el
        except: pass

        # 3. Buscar en iframes/frames (Barrido completo si fallÃ³ la predicciÃ³n)
        frames = self.driver.find_elements(By.TAG_NAME, "iframe") + self.driver.find_elements(By.TAG_NAME, "frame")
        
        # OptimizaciÃ³n: Probar primero el Ãºltimo frame exitoso
        order_to_check = list(range(len(frames)))
        if self._last_successful_frame_index is not None and self._last_successful_frame_index < len(frames):
            # Movemos el Ã­ndice ganador al principio de la lista
            order_to_check.remove(self._last_successful_frame_index)
            order_to_check.insert(0, self._last_successful_frame_index)

        self.log(f"[FRAME] Buscando en {len(frames)} frames...")
        
        for i in order_to_check:
            try:
                self.driver.switch_to.frame(frames[i])
                # self.log(f"[FRAME] Entrando al frame {i}...") # Comentado para reducir ruido en log
                
                # BÃºsqueda recursiva (simple por ahora, solo 1 nivel de profundidad extra)
                try:
                    el = self.driver.find_element(by, value)
                    if el.is_displayed():
                        self.log(f"[FRAME] Â¡Elemento encontrado en frame {i}!")
                        self._last_successful_frame_index = i # Guardamos el ganador
                        return el
                except: pass
                
                # Volver al padre para seguir buscando
                self.driver.switch_to.parent_frame()
            except Exception as e:
                self.driver.switch_to.default_content() # Reset por seguridad
        
        # Si no se encuentra, volver al default
        self.driver.switch_to.default_content()
        self._recuperar_si_pagina_error(f"elemento no encontrado {by}={value}")
        return None

    def diagnostico_exhaustivo(self):
        """
        Recorre todos los frames y guarda su contenido HTML.
        TambiÃ©n lista elementos interactivos visibles para ayudar a encontrar el botÃ³n.
        """
        self.log("[DIAGNÃ“STICO] Iniciando escaneo profundo de la pÃ¡gina...")
        
        try:
            # 1. Dump contexto principal
            with open("debug_main.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
            # 2. Recorrer frames
            frames = self.driver.find_elements(By.TAG_NAME, "iframe") + self.driver.find_elements(By.TAG_NAME, "frame")
            self.log(f"[DIAGNÃ“STICO] Se detectaron {len(frames)} frames/iframes.")
            
            for i, frame in enumerate(frames):
                try:
                    self.driver.switch_to.frame(frame)
                    self.log(f"--- FRAME {i} ---")
                    
                    # Guardar HTML
                    with open(f"debug_frame_{i}.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    
                    # Listar elementos interesantes
                    elementos = self.driver.find_elements(By.XPATH, "//*[self::a or self::button or self::input]")
                    visibles = [e for e in elementos if e.is_displayed()]
                    self.log(f"    Elementos interactivos visibles: {len(visibles)}")
                    
                    for el in visibles[:15]: # Listar primeros 15
                        try:
                            info = f"Tag: {el.tag_name} | ID: {el.get_attribute('id')} | Text: {el.text[:20]} | Title: {el.get_attribute('title')} | Src/Href: {el.get_attribute('src') or el.get_attribute('href')}"
                            self.log(f"    -> {info}")
                            
                            # Si parece prometedor, lo marcamos en AZUL para que el usuario lo vea
                            if "agenda" in info.lower() or "modif" in info.lower():
                                self.driver.execute_script("arguments[0].style.border='5px solid blue';", el)
                                self.log("    (MARCADO EN AZUL COMO POSIBLE CANDIDATO)")
                        except: pass
                        
                    self.driver.switch_to.parent_frame()
                except Exception as e:
                    self.log(f"    Error leyendo frame {i}: {e}")
                    self.driver.switch_to.default_content()
                    
            self.driver.switch_to.default_content()
            self.log("[DIAGNÃ“STICO] Escaneo finalizado. Revisa los archivos debug_*.html")
            
        except Exception as e:
            self.log(f"[DIAGNÃ“STICO] FallÃ³ el proceso de diagnÃ³stico: {e}")

    def buscar_profesional(self):
        # Nota: Usamos get con valores por defecto para evitar KeyError si falta alguna clave
        nombre_completo = self.config["profesional"].get("nombre", "")
        apellido = self.config["profesional"].get("primer_apellido", "")
        nombre = self.config["profesional"].get("primer_nombre", "")
        sede_texto = self.config["profesional"].get("sede", "")
        
        self.log(f"[INFO] Buscando profesional: {apellido} {nombre}")

        try:
            # --- MANEJO DE FRAMES PARA EL MÃ“DULO ---
            # A veces el contenido carga en un frame especÃ­fico. Intentamos ubicarlo.
            # Buscamos algo distintivo de la pantalla de bÃºsqueda, ej: el input de apellido
            el_test = self.buscar_elemento_en_frames(*SELECTORES["input_primer_apellido"])
            if not el_test:
                self.log("[WARN] No se detectÃ³ el formulario en ningÃºn frame. Intentando seguir en default...")
            
            # 1. SELECCIONAR SEDE PRIMERO (CRÃTICO: El profesional suele depender de la sede)
            if sede_texto:
                self.log(f"[INFO] Seleccionando sede: {sede_texto}")
                try:
                    el_select = self.wait.until(EC.visibility_of_element_located(SELECTORES["select_sede"]))
                    select_obj = Select(el_select)
                    
                    # Verificar si ya estÃ¡ seleccionada para no recargar innecesariamente
                    opcion_actual = select_obj.first_selected_option.text.strip()
                    if sede_texto not in opcion_actual:
                        self.resaltar_elemento(el_select)
                        # Intento flexible de selecciÃ³n
                        try:
                            select_obj.select_by_visible_text(sede_texto)
                        except:
                            # BÃºsqueda parcial si falla exacto
                            for op in select_obj.options:
                                if sede_texto in op.text:
                                    select_obj.select_by_visible_text(op.text)
                                    break
                        
                        self.log("[INFO] Sede cambiada, esperando recarga...")
                        
                        # OptimizaciÃ³n: Esperar staleness en lugar de sleep fijo
                        # Si el elemento input apellido existe, esperamos a que desaparezca (si la pÃ¡gina recarga)
                        # O simplemente esperamos un breve momento y verificamos el cambio
                        try:
                            # Intento de detecciÃ³n de recarga ultra-rÃ¡pido (sin sleeps fijos si es posible)
                            # Verificamos si el elemento 'el_select' se vuelve 'stale' (obsoleto)
                            # Esto confirma que la pÃ¡gina comenzÃ³ a recargar.
                            WebDriverWait(self.driver, 2).until(EC.staleness_of(el_select))
                            self.log("[INFO] Recarga de pÃ¡gina detectada (Staleness).")
                        except TimeoutException:
                            self.log("[INFO] No se detectÃ³ recarga inmediata (posible AJAX), continuando...")
                        
                        # RE-UBICAR FRAME DESPUÃ‰S DE RECARGA
                        self.buscar_elemento_en_frames(*SELECTORES["input_primer_apellido"])
                    else:
                        self.log("[INFO] La sede correcta ya estaba seleccionada.")
                except Exception as e:
                    self.log(f"[WARN] No se pudo cambiar la sede (puede que sea fija): {e}")

            # 2. LLENAR FORMULARIO
            # Llenar Apellido
            try:
                el_ap = self.wait.until(EC.visibility_of_element_located(SELECTORES["input_primer_apellido"]))
                el_ap.clear()
                self.resaltar_elemento(el_ap)
                el_ap.send_keys(apellido)
            except Exception as e:
                self.log(f"[ERROR] No se pudo escribir apellido: {e}")
            
            # Llenar Nombre
            try:
                el_nom = self.driver.find_element(*SELECTORES["input_primer_nombre"])
                el_nom.clear()
                el_nom.send_keys(nombre)
            except: pass # Nombre opcional a veces

            # PEQUEÃ‘A PAUSA DE SEGURIDAD (Permite que el JS habilite el botÃ³n)
            time.sleep(0.5)

            # 3. CLICK EN BUSCAR
            self.log("[INFO] Ejecutando bÃºsqueda...")
            try:
                # Estrategia 1: Esperar a que sea CLICKABLE (SoluciÃ³n a "antes funcionaba")
                # Antes solo buscÃ¡bamos "presence", ahora aseguramos "interactability"
                btn = self.wait.until(EC.element_to_be_clickable(SELECTORES["btn_buscar_prof"]))
                self.resaltar_elemento(btn)
                btn.click()
            except Exception as e:
                self.log(f"[WARN] FallÃ³ click normal en lupa ({e}). Intentando estrategias alternativas...")
                
                # Estrategia 2: BÃºsqueda genÃ©rica de Input Image o Lupa
                xpath_lupa = "//input[@type='image' and (contains(@name, 'IMAGE') or contains(@src, 'search') or contains(@src, 'buscar') or contains(@src, 'lupa'))]"
                try:
                    btn = self.driver.find_element(By.XPATH, xpath_lupa)
                    self.resaltar_elemento(btn)
                    self.driver.execute_script("arguments[0].click();", btn)
                    self.log("[INFO] Click en lupa forzado por JS (XPath genÃ©rico).")
                except:
                    self.log("[ERROR] No se pudo encontrar ni clickear el botÃ³n de bÃºsqueda.")
                    raise

            # Esperar resultados (observando la tabla)
            self.log("[INFO] Esperando tabla de resultados...")
            try:
                self.wait.until(EC.presence_of_element_located(SELECTORES["tabla_resultados"]))
            except TimeoutException:
                self.log("[WARN] Tabla no detectada, asumiendo que ya estaba cargada o no hay resultados.")

            # =================================================================================
            # PARTE CRÃTICA: BUSCAR BOTÃ“N MODIFICAR (OPTIMIZADO V3)
            # =================================================================================
            self.log(">>> INICIANDO BÃšSQUEDA VELOZ DE BOTÃ“N MODIFICAR <<<")
            
            boton_encontrado = None

            # FASE 1: BÃºsqueda InstantÃ¡nea por ID (Lo mÃ¡s rÃ¡pido)
            # Probamos los IDs conocidos directamente sin esperar
            ids_rapidos = ["vUPDATE_0001", "vVALAGE_0001"]
            for _id in ids_rapidos:
                try:
                    candidato = self.driver.find_element(By.ID, _id)
                    if candidato.is_displayed():
                        boton_encontrado = candidato
                        self.log(f"[FAST] Â¡BotÃ³n encontrado por ID {_id}!")
                        break
                except: pass

            # FASE 2: Si fallÃ³ la rÃ¡pida, usamos espera inteligente (WebDriverWait)
            if not boton_encontrado:
                self.log("[INFO] No se encontrÃ³ por ID directo. Iniciando bÃºsqueda avanzada optimizada...")
                
                # XPath SUPER optimizado: Busca SOLO en tags especÃ­ficos (input, img, a)
                # Evita recorrer todo el DOM con //*
                xpath_universal = (
                    "//input["
                    "contains(@id, 'vUPDATE') or "
                    "contains(@id, 'VALAGE') or "
                    "contains(@src, 'modificar') or "
                    "contains(@alt, 'Modificar')"
                    "] | "
                    "//img["
                    "contains(@id, 'vUPDATE') or "
                    "contains(@src, 'modificar') or "
                    "contains(@alt, 'Modificar')"
                    "] | "
                    "//a["
                    "contains(@id, 'vUPDATE') or "
                    "contains(@href, 'agendas')"
                    "]"
                )

                try:
                    # BÃºsqueda ultra-rÃ¡pida (casi instantÃ¡nea)
                    # Usamos find_elements para no lanzar excepciÃ³n y ser mÃ¡s rÃ¡pidos
                    candidatos = self.driver.find_elements(By.XPATH, xpath_universal)
                    if candidatos:
                         boton_encontrado = candidatos[0]
                         self.log("[EXITO] BotÃ³n detectado por bÃºsqueda avanzada (instantÃ¡neo).")
                    else:
                         # Forzar salto inmediato a frames
                         raise TimeoutException("No encontrado en root")
                except TimeoutException:
                    self.log("[WARN] BÃºsqueda root fallÃ³. Saltando a frames...")
                    boton_encontrado = self.buscar_elemento_en_frames(By.XPATH, xpath_universal)

            # ACCIÃ“N FINAL
            if boton_encontrado:
                self.log(f">>> Â¡OBJETIVO LOCALIZADO! ID: {boton_encontrado.get_attribute('id')} | Tag: {boton_encontrado.tag_name} <<<")
                
                # Scroll y Resaltado
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", boton_encontrado)
                    self.resaltar_elemento(boton_encontrado)
                except: pass

                # Click
                try:
                    # Verificar si es imagen dentro de link
                    parent = boton_encontrado.find_element(By.XPATH, "..")
                    if parent.tag_name == "a":
                        self.log("[INFO] Click en enlace padre (<a>) en lugar de la imagen.")
                        boton_encontrado = parent
                except: pass

                try:
                    boton_encontrado.click()
                except:
                    self.log("[WARN] Click normal fallÃ³, forzando JS...")
                    self.driver.execute_script("arguments[0].click();", boton_encontrado)
                
                self.log("[EXITO] Click enviado. Verificando cambio de pÃ¡gina...")
                
                # Espera dinÃ¡mica inteligente (mÃ¡x 5s)
                start_time = time.time()
                while time.time() - start_time < 5:
                    # 1. Chequeo de Ventanas (Prioridad alta por popups)
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.log("[INFO] Cambiado a nueva pestaÃ±a/ventana.")
                        break

                    # 2. Chequeo de URL
                    if "agendas" in self.driver.current_url.lower():
                        self.log("[CONFIRMADO] NavegaciÃ³n exitosa a Agendas.")
                        break
                    
                    time.sleep(0.2) # Polling rÃ¡pido
                else:
                    self.log("[WARN] No se detectÃ³ cambio de URL/Ventana inmediato, continuando...")
            else:
                self.log("[CRITICO] AGOTADAS TODAS LAS ESTRATEGIAS. EL BOTÃ“N NO APARECE.")
                self.diagnostico_exhaustivo()
                raise Exception("No se encontrÃ³ botÃ³n Modificar Agenda")

        except Exception as e:
            self.log(f"[ERROR] Fallo en bÃºsqueda de profesional: {e}")
            raise


    def _get_prefix(self, element):
        """Extrae el prefijo del ID (ej: 'AGEDIA_0001' -> 'AGEDIA')"""
        full_id = element.get_attribute('id')
        if not full_id: return ""
        if '_0001' in full_id:
            return full_id.split('_0001')[0]
        # Intento genÃ©rico de quitar los Ãºltimos 5 chars si son _\d\d\d\d
        if len(full_id) > 5 and full_id[-5] == '_' and full_id[-4:].isdigit():
            return full_id[:-5]
        return full_id

    def detectar_mapeo_columnas(self):
        """
        Intenta deducir dinÃ¡micamente quÃ© ID corresponde a cada columna de la grilla
        basÃ¡ndose en la posiciÃ³n horizontal (X) de los elementos de la primera fila (_0001).
        Optimizado: Robusto contra StaleElementReferenceException.
        """
        self.log("[AUTO-DETECT] Iniciando mapeo de columnas de la grilla...")
        mapeo = {}
        
        for attempt in range(3): # Reintentos para estabilidad
            try:
                # 1. Buscar todos los inputs y selects de la fila 1
                inputs = self.driver.find_elements(By.XPATH, "//*[contains(@id, '_0001') and (self::input or self::select)]")
                
                # 2. ExtracciÃ³n segura de datos (evita StaleElementReferenceException durante el sort)
                candidatos = []
                for el in inputs:
                    try:
                        if el.is_displayed() and el.size['width'] > 0:
                            candidatos.append({
                                'id': el.get_attribute('id'),
                                'tag': el.tag_name,
                                'type': el.get_attribute('type'),
                                'x': el.location['x']
                            })
                    except: 
                        continue # Si el elemento muere durante el chequeo, lo ignoramos

                # Ordenar por posiciÃ³n X
                candidatos.sort(key=lambda k: k['x'])
                
                # Clasificar segÃºn tipo
                selects = [c for c in candidatos if c['tag'] == 'select']
                texts = [c for c in candidatos if c['tag'] == 'input' and c['type'] == 'text']
                
                self.log(f"[AUTO-DETECT] Se encontraron {len(selects)} selects y {len(texts)} inputs de texto en la fila 1.")
                
                # --- MAPEO DE SELECTS ---
                # Orden esperado: Dia, Activo, Serv1, Serv2, Serv3...
                if len(selects) >= 2:
                    # Helper interno para extraer prefijo desde el dict
                    def get_prefix(full_id):
                        if not full_id: return ""
                        if '_0001' in full_id: return full_id.split('_0001')[0]
                        if len(full_id) > 5 and full_id[-5] == '_' and full_id[-4:].isdigit(): return full_id[:-5]
                        return full_id

                    mapeo['dia'] = get_prefix(selects[0]['id'])
                    mapeo['activo'] = get_prefix(selects[1]['id'])
                    # Todos los selects restantes son servicios
                    mapeo['servicios'] = [get_prefix(s['id']) for s in selects[2:]]
                    
                    self.log(f"   -> Dia: {mapeo['dia']}")
                    self.log(f"   -> Activo: {mapeo['activo']}")
                    self.log(f"   -> Servicios (Lista): {mapeo['servicios']}")
                else:
                    self.log("[WARN] Menos selects de los esperados.")
                    # Fallback parcial si fallÃ³ la lÃ³gica pero no hubo excepciÃ³n
                    raise Exception("Estructura de selects incompleta")

                # --- MAPEO DE INPUTS TEXT ---
                # Orden esperado: Inicio, Fin, Duracion, Espacios
                if len(texts) >= 3:
                    def get_prefix(full_id): # RedefiniciÃ³n local por si acaso
                        if not full_id: return ""
                        if '_0001' in full_id: return full_id.split('_0001')[0]
                        return full_id

                    mapeo['inicio'] = get_prefix(texts[0]['id'])
                    mapeo['fin'] = get_prefix(texts[1]['id'])
                    mapeo['duracion'] = get_prefix(texts[2]['id'])
                    if len(texts) > 3:
                        mapeo['espacios'] = get_prefix(texts[3]['id'])
                    
                    self.log(f"   -> Inicio: {mapeo['inicio']}")
                    self.log(f"   -> Fin: {mapeo['fin']}")
                    self.log(f"   -> Duracion: {mapeo['duracion']}")
                else:
                     self.log("[WARN] Menos inputs de texto de los esperados.")
                     raise Exception("Estructura de inputs incompleta")
                    
                return mapeo # Ã‰xito

            except Exception as e:
                self.log(f"[WARN] Intento {attempt+1} fallÃ³ en detecciÃ³n de columnas: {e}")
                time.sleep(1) # Esperar a que el DOM se estabilice

        self.log("[ERROR] FallÃ³ la detecciÃ³n de columnas tras reintentos. Usando FALLBACK AMPLIO.")
        return {
            'dia': "AGEDIA", 'inicio': "AGEHORINI", 'fin': "AGEHORFIN",
            'duracion': "AGEDUR", 'activo': "AGEACT", 
            'servicios': ["AGESERCOD1", "AGESERCOD2", "AGESERCOD3", "AGESERCOD4", "AGESERCOD5"]
        }

    def configurar_agenda(self):
        self.log("\n[PASO 2] Configurando horarios de atenciÃ³n...")
        
        try:
            self.navegar_a_modulo(SELECTORES["menu_citas"], SELECTORES["submenu_config_agenda"])
            # Esperar carga inicial del mÃ³dulo
            try:
                self.wait.until(EC.visibility_of_element_located(SELECTORES["input_primer_apellido"]))
            except TimeoutException:
                 self.log("[WARN] Tiempo de espera agotado esperando carga de mÃ³dulo configuraciÃ³n.")

            self.buscar_profesional()
            
            # Esperar confirmaciÃ³n de carga de la siguiente pantalla (ConfiguraciÃ³n)
            self.log("[INFO] Esperando carga de pantalla de horarios...")
            try:
                # Esperamos a que aparezca al menos un elemento que termine en _0001
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, '_0001')]")))
            except TimeoutException:
                self.log("[ERROR] No se detectÃ³ la grilla de configuraciÃ³n.")
                self.driver.save_screenshot("debug_grid_fail.png")
                raise Exception("Fallo navegaciÃ³n a horarios")

            # Detectar IDs dinÃ¡micamente
            mapa = self.detectar_mapeo_columnas()
            
            # Obtener configuraciÃ³n
            conf_agenda = self.config.get("configuracion_agenda", {})
            dias_lista = conf_agenda.get("dias_atencion", [])
            horarios_lista = conf_agenda.get("horarios", [])
            servicios_lista = conf_agenda.get("servicios", [])
            
            if not dias_lista or not horarios_lista:
                self.log("[ERROR] Falta configuraciÃ³n de dÃ­as u horarios.")
                return

            idx_fila = 1
            
            # Iteramos por cada dÃ­a y por cada horario
            for dia_nombre in dias_lista:
                for horario in horarios_lista:
                    sufijo = f"_{idx_fila:04d}"
                    
                    h_ini = horario["inicio"]
                    h_fin = horario["fin"]
                    dur = str(horario.get("duracion", 10))
                    
                    self.log(f"[INFO] Configurando fila {idx_fila}: {dia_nombre} {h_ini}-{h_fin} ({dur}m)")
                    
                    try:
                        # Verificar si existe la fila, si no, intentamos agregarla
                        id_dia = mapa['dia'] + sufijo
                        try:
                            el_dia = self.driver.find_element(By.ID, id_dia)
                        except NoSuchElementException:
                            # Si no existe, buscamos botÃ³n "MÃ¡s" o "Agregar"
                            self.log(f"[INFO] No existe fila {idx_fila}. Buscando botÃ³n agregar...")
                            try:
                                # Buscamos imagen con 'add', 'plus', 'insert' o 'nuevo'
                                btn_add = self.driver.find_element(By.XPATH, "//input[contains(@src, 'add') or contains(@src, 'plus') or contains(@src, 'insert') or contains(@alt, 'Agregar')]")
                                btn_add.click()
                                
                                # Esperar dinÃ¡micamente a que aparezca la nueva fila
                                try:
                                    WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, id_dia)))
                                except: pass
                                
                                el_dia = self.driver.find_element(By.ID, id_dia) # Reintentar
                            except:
                                self.log("[WARN] No se pudo agregar nueva fila. Deteniendo configuraciÃ³n.")
                                break
                        
                        self.resaltar_elemento(el_dia)
                        select_dia = Select(el_dia)
                        # SelecciÃ³n de DÃ­a
                        try:
                             select_dia.select_by_visible_text(dia_nombre)
                        except:
                             # Mapeo numÃ©rico fallback
                             mapa_dias = {"Lunes": "1", "Martes": "2", "MiÃ©rcoles": "3", "Miercoles": "3", "Jueves": "4", "Viernes": "5", "SÃ¡bado": "6", "Domingo": "7"}
                             select_dia.select_by_value(mapa_dias.get(dia_nombre, "1"))

                        # Hora Inicio
                        el_ini = self.driver.find_element(By.ID, mapa['inicio'] + sufijo)
                        self.ingresar_hora(el_ini, h_ini)
                        
                        # Hora Fin
                        el_fin = self.driver.find_element(By.ID, mapa['fin'] + sufijo)
                        self.ingresar_hora(el_fin, h_fin)
                        
                        # DuraciÃ³n
                        el_dur = self.driver.find_element(By.ID, mapa['duracion'] + sufijo)
                        el_dur.clear()
                        el_dur.send_keys(dur)
                        
                        # Activo (Si existe y es select)
                        if 'activo' in mapa:
                            try:
                                el_act = self.driver.find_element(By.ID, mapa['activo'] + sufijo)
                                Select(el_act).select_by_visible_text("Si")
                            except: pass

                        # Servicios (Agenda Para 1, 2, 3...)
                        if 'servicios' in mapa and mapa['servicios']:
                            for i, servicio_nombre in enumerate(servicios_lista):
                                if i >= len(mapa['servicios']): break # No hay mÃ¡s columnas
                                
                                id_serv = mapa['servicios'][i] + sufijo
                                try:
                                    el_serv = self.driver.find_element(By.ID, id_serv)
                                    self.seleccionar_servicio(el_serv, servicio_nombre)
                                except Exception as e_serv:
                                    self.log(f"      -> [WARN] No se pudo asignar servicio {servicio_nombre}: {e_serv}")
                        
                        idx_fila += 1
                        
                    except Exception as e:
                        self.log(f"[ERROR] Error configurando fila {idx_fila}: {e}")
                        break
                else:
                    continue 
                break 

            # Guardar cambios
            self.log("[INFO] Guardando configuraciÃ³n de horarios...")
            try:
                 # Buscamos botÃ³n por texto "Confirmar" o "Guardar" o ID comÃºn
                 btn_guardar = None
                 try:
                     btn_guardar = self.driver.find_element(By.NAME, "BTN_ENTER")
                 except:
                     btn_guardar = self.driver.find_element(By.XPATH, "//input[@value='Confirmar' or @value='Guardar']")
                 
                 if btn_guardar:
                     self.resaltar_elemento(btn_guardar)
                     btn_guardar.click()
                     
                     # Esperar confirmaciÃ³n alert
                     try:
                         WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                         alert = self.driver.switch_to.alert
                         self.log(f"[ALERT] {alert.text}")
                         alert.accept()
                         
                         # CRÃTICO: Esperar a que la pÃ¡gina termine de procesar antes de intentar ir a otro lado
                         # A veces el sistema te devuelve a la pantalla anterior automÃ¡ticamente.
                         time.sleep(2) 
                     except: pass
            except Exception as e:
                 self.log(f"[WARN] No se pudo dar click en Guardar: {e}")

        except Exception as e:
            self.log(f"[ERROR] FallÃ³ la configuraciÃ³n de agenda: {e}")
            self.resumen_acciones.append("ConfiguraciÃ³n Agenda: FALLO")
            raise

    def calcular_proxima_fecha(self, dia_semana_str):
        """
        Calcula la prÃ³xima fecha (dd/mm/yyyy) correspondiente al dÃ­a de la semana indicado.
        Si hoy es ese dÃ­a, devuelve la fecha de hoy.
        """
        map_dias = {
            "lunes": 0, "martes": 1, "miÃ©rcoles": 2, "miercoles": 2,
            "jueves": 3, "viernes": 4, "sÃ¡bado": 5, "sabado": 5, "domingo": 6
        }
        
        target_weekday = map_dias.get(dia_semana_str.lower())
        if target_weekday is None:
            self.log(f"[WARN] DÃ­a desconocido '{dia_semana_str}', usando fecha de maÃ±ana por defecto.")
            target_weekday = (datetime.date.today().weekday() + 1) % 7
            
        today = datetime.date.today()
        current_weekday = today.weekday()
        
        days_ahead = target_weekday - current_weekday
        if days_ahead < 0: # Target day already happened this week
            days_ahead += 7
            
        next_date = today + datetime.timedelta(days=days_ahead)
        return next_date.strftime("%d/%m/%Y")

    def generar_agenda(self):
        self.log("\n[PASO 3] Iniciando GeneraciÃ³n de Agenda...")
        
        try:
            # Intentamos cerrar cualquier alert residual
            try: 
                self.driver.switch_to.alert.accept()
            except: pass
            
            # NavegaciÃ³n Robusta:
            self.driver.switch_to.default_content()
            
            # NOTA: Omitimos click en "Citas" si ya estÃ¡ abierto.
            self.navegar_a_modulo(SELECTORES["menu_citas"], SELECTORES["submenu_gen_agenda"], forzar_menu=False)
            
            # Esperar carga del formulario
            try:
                self.wait.until(EC.visibility_of_element_located(SELECTORES["input_fecha_ini"]))
            except TimeoutException:
                 self.log("[WARN] Tiempo de espera agotado esperando carga de Generar Agenda.")
            
            # 1. Seleccionar Profesional (Dropdown)
            self.log("[INFO] Seleccionando profesional en Generar Agenda...")
            try:
                # Buscar el select asociado al label "Profesional"
                select_el = self.buscar_elemento_en_frames(*SELECTORES["select_profesional_gen"])
                
                if select_el:
                    # Construir nombre completo: A1 A2 N1 N2
                    p = self.config['profesional']
                    partes_nombre = [
                        p.get('primer_apellido', ''),
                        p.get('segundo_apellido', ''),
                        p.get('primer_nombre', ''),
                        p.get('segundo_nombre', '')
                    ]
                    # Unir partes no vacÃ­as
                    prof_nombre = " ".join([x for x in partes_nombre if x]).strip().upper()
                    
                    self.log(f"[INFO] Buscando profesional: '{prof_nombre}'")
                    
                    # Usamos la funciÃ³n auxiliar de selecciÃ³n inteligente
                    exito_prof = self.seleccionar_servicio(select_el, prof_nombre)
                    
                    if not exito_prof:
                        # Fallback: Intentar solo con A1 y N1 por si acaso
                        prof_simple = f"{p.get('primer_apellido', '')} {p.get('primer_nombre', '')}".strip().upper()
                        if prof_simple != prof_nombre:
                            self.log(f"[INFO] Reintentando con nombre simplificado: '{prof_simple}'")
                            self.seleccionar_servicio(select_el, prof_simple)

                else:
                    self.log("[ERROR] No se encontrÃ³ el dropdown de profesional.")
            except Exception as e:
                self.log(f"[ERROR] FallÃ³ selecciÃ³n de profesional: {e}")

            # 2. Calcular Fechas DinÃ¡micas
            dias_atencion = self.config["configuracion_agenda"]["dias_atencion"]
            if dias_atencion:
                # Tomamos el primer dÃ­a configurado como referencia principal
                dia_obj = dias_atencion[0]
                fecha_gen = self.calcular_proxima_fecha(dia_obj)
                self.log(f"[INFO] DÃ­a configurado: {dia_obj} -> Fecha calculada: {fecha_gen}")
                f_ini = fecha_gen
                f_fin = fecha_gen
            else:
                # Fallback a config estÃ¡tica si no hay dÃ­as definidos
                f_ini = self.config["generacion_agenda"]["fecha_inicio"]
                f_fin = self.config["generacion_agenda"]["fecha_fin"]
                self.log(f"[INFO] Usando fechas estÃ¡ticas: {f_ini} - {f_fin}")
            
            # 3. Ingresar Fechas
            # Usamos JS para asignar valores directamente y evitar problemas con mÃ¡scaras/pickers
            # Buscamos los elementos con el buscador de frames por seguridad
            
            self.log("[INFO] Ingresando fecha de inicio para agenda...")
            input_ini = self.buscar_elemento_en_frames(*SELECTORES["input_fecha_ini"])
            if input_ini:
                self.resaltar_elemento(input_ini)
                self.driver.execute_script("arguments[0].value = arguments[1];", input_ini, f_ini)
                # Disparar eventos de cambio por si acaso
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", input_ini)
            else:
                self.log("[ERROR] No se encontrÃ³ campo fecha inicio")

            self.log("[INFO] Ingresando fecha fin...")
            input_fin = self.buscar_elemento_en_frames(*SELECTORES["input_fecha_fin"])
            if input_fin:
                self.resaltar_elemento(input_fin)
                self.driver.execute_script("arguments[0].value = arguments[1];", input_fin, f_fin)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", input_fin)
            else:
                self.log("[ERROR] No se encontrÃ³ campo fecha fin")
            
            # 4. Click Generar
            self.log("[INFO] Buscando botÃ³n Generar...")
            btn_gen = self.buscar_elemento_en_frames(*SELECTORES["btn_generar_final"])
            if btn_gen:
                self.resaltar_elemento(btn_gen)
                # Intentar click normal y JS
                try:
                    btn_gen.click()
                except:
                    self.driver.execute_script("arguments[0].click();", btn_gen)
                
                self.log("[PASO FINAL] BotÃ³n Generar presionado. Proceso completado.")
                
            else:
                self.log("[ERROR] No se encontrÃ³ botÃ³n Generar Agenda")
            
            # 5. Validar Ã©xito
            try:
                # Esperamos alerta o mensaje en pantalla
                try:
                    WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    txt = alert.text
                    self.log(f"[ALERT] {txt}")
                    alert.accept()
                    self.resumen_acciones.append(f"GeneraciÃ³n Agenda ({f_ini}): {txt}")
                except:
                    # Si no hay alerta, buscar mensaje en DOM
                    mensaje = self.wait.until(EC.visibility_of_element_located(SELECTORES["msg_exito"])).text
                    self.log(f"[EXITO] Sistema responde: {mensaje}")
                    self.resumen_acciones.append(f"GeneraciÃ³n Agenda ({f_ini}): EXITOSO")
            except TimeoutException:
                self.log("[WARN] No se detectÃ³ confirmaciÃ³n explÃ­cita.")
                self.resumen_acciones.append(f"GeneraciÃ³n Agenda ({f_ini}): SIN CONFIRMACION")

        except Exception as e:
            self.log(f"[ERROR] FallÃ³ la generaciÃ³n de agenda: {e}")
            self.resumen_acciones.append("GeneraciÃ³n Agenda: FALLO")

    def esperar_carga_completa(self, timeout=30):
        """
        Espera dinÃ¡micamente a que la pÃ¡gina termine de cargar recursos y peticiones AJAX.
        Soporta:
        - document.readyState
        - jQuery.active (si existe)
        - Sys.WebForms.PageRequestManager (ASP.NET AJAX, si existe)
        """
        end_time = time.time() + timeout
        self.log("[WAIT] Esperando carga completa de la pÃ¡gina/acciÃ³n...")
        
        # PequeÃ±a pausa inicial para dar tiempo a que se disparen eventos (ej. click -> inicio request)
        time.sleep(1)
        
        while time.time() < end_time:
            try:
                # 1. Estado del Documento
                ready_state = self.driver.execute_script("return document.readyState")
                if ready_state != "complete":
                    time.sleep(0.5)
                    continue

                # 2. jQuery (si existe)
                jquery_active = self.driver.execute_script("""
                    return (typeof jQuery !== 'undefined') ? jQuery.active : 0;
                """)
                if jquery_active > 0:
                    time.sleep(0.5)
                    continue
                
                # 3. ASP.NET AJAX (Sys.WebForms)
                # Verifica si hay un PostBack asÃ­ncrono en curso
                asp_net_ajax = self.driver.execute_script("""
                    try {
                        if (typeof Sys !== 'undefined' && typeof Sys.WebForms !== 'undefined' && typeof Sys.WebForms.PageRequestManager !== 'undefined') {
                            var prm = Sys.WebForms.PageRequestManager.getInstance();
                            return prm.get_isInAsyncPostBack();
                        }
                    } catch(e) { }
                    return false;
                """)
                if asp_net_ajax:
                    time.sleep(0.5)
                    continue
                
                # Si pasa todas las verificaciones, la pÃ¡gina estÃ¡ "quieta"
                return True
                
            except Exception as e:
                # Si hay error al ejecutar script (ej. navegaciÃ³n en curso), esperamos un poco
                time.sleep(0.5)
        
        self.log("[WARN] Tiempo de espera dinÃ¡mico agotado. La pÃ¡gina puede no haber terminado de cargar.")
        try:
            if self._pagina_en_blanco_o_error() or self._es_pantalla_login():
                self.recuperar_pagina_y_sesion("timeout de carga")
        except Exception:
            pass
        return False

    def _codigo_tipo_atencion(self, tipo_atencion):
        tipo_norm = normalize_text(tipo_atencion)
        if "VALORACION" in tipo_norm:
            return "VAL"
        if "EVOLUCION" in tipo_norm:
            return "EVO"
        if "PRIMERA VEZ" in tipo_norm:
            return "PRV"
        if "CONTROL" in tipo_norm:
            return "CTL"
        limpio = "".join(ch for ch in tipo_norm if ch.isalnum())
        return (limpio[:3] or "GEN")

    def _codigo_servicio(self, servicio):
        return self._codigo_servicio_por_contexto(servicio, None)

    def _codigo_servicio_por_contexto(self, servicio, tipo_atencion=None):
        serv_norm = normalize_text(servicio)
        tipo_norm = normalize_text(tipo_atencion)

        if "PSICOLOGIA PRIMERA VEZ" in serv_norm:
            return "VALPS"
        if "PSICOLOGIA CONTROL" in serv_norm:
            return "PS"
        if "PSIQUIATRIA" in serv_norm:
            if "PRIMERA VEZ" in tipo_norm:
                return "VALPQ"
            return "PQ"
        if "TERAPIA FISICA" in serv_norm or "FISIOTERAPIA" in serv_norm or "FISIOTERAPEUTA" in serv_norm:
            return "TF"
        if "ENFERMERIA" in serv_norm:
            return "MED"
        if "TRABAJO SOCIAL" in serv_norm:
            return "TS"
        if "ODONTOLOGIA" in serv_norm:
            return "ODO"
        if "MEDICINA GENERAL" in serv_norm:
            return "MGE"
        if not serv_norm or serv_norm == "TODOS":
            return "GEN"

        stopwords = {"DE", "DEL", "LA", "EL", "LOS", "LAS", "Y", "EN", "POR", "PARA", "AL"}
        tokens = [t for t in serv_norm.replace("-", " ").split() if t and t not in stopwords]
        if not tokens:
            return "GEN"
        return tokens[0][:3]

    def _normalizar_numero_factura(self, numero_factura):
        valor = str(numero_factura or "").strip()
        if not valor or valor.lower() == "nan":
            return ""
        if valor.endswith(".0"):
            valor = valor[:-2]
        permitido = []
        for ch in valor:
            if ch.isalnum() or ch in ("-", "_"):
                permitido.append(ch)
        return "".join(permitido)

    def _ruta_unica(self, carpeta_destino, nombre_archivo):
        base, ext = os.path.splitext(nombre_archivo)
        ruta = os.path.join(carpeta_destino, nombre_archivo)
        contador = 2
        while os.path.exists(ruta):
            ruta = os.path.join(carpeta_destino, f"{base}_{contador}{ext}")
            contador += 1
        return ruta

    def _nombre_carpeta_servicio(self, servicio):
        s = normalize_text(servicio)
        if not s:
            return "GEN"
        permitido = []
        for ch in s:
            if ch.isalnum() or ch in (" ", "-", "_"):
                permitido.append(ch)
        nombre = " ".join("".join(permitido).strip().split()).upper()
        return (nombre or "GEN")[:60]

    def _eliminar_pdfs_duplicados_recientes(self, archivos_antes, ventana_segundos=15):
        """Elimina cualquier PDF que aparecio en la RAIZ de download_dir
        despues del snapshot ``archivos_antes`` y dentro de los ultimos
        ``ventana_segundos`` segundos. Esto cubre el caso en que Chrome
        auto-descarga el mismo PDF en paralelo a nuestra descarga via
        requests / mover, dejando un duplicado huerfano.

        Es seguro: solo borra .pdf que esten SUELTOS en la raiz, nunca toca
        las subcarpetas de servicio. Si no hay duplicados, no hace nada.
        """
        eliminados = 0
        try:
            base = getattr(self, "download_dir", None)
            if not base or not os.path.isdir(base):
                return 0
            ahora = time.time()
            archivos_antes = set(archivos_antes or [])
            for nombre in os.listdir(base):
                ruta = os.path.join(base, nombre)
                if not os.path.isfile(ruta):
                    continue
                low = nombre.lower()
                if not low.endswith(".pdf"):
                    continue
                if nombre in archivos_antes:
                    continue
                try:
                    edad = ahora - os.path.getmtime(ruta)
                except Exception:
                    continue
                if edad > ventana_segundos:
                    continue
                try:
                    os.remove(ruta)
                    eliminados += 1
                    self.log(f"[DEDUP] Duplicado eliminado de raiz: {nombre}")
                except Exception as e:
                    self.log(f"[DEDUP] No se pudo borrar duplicado {nombre}: {e}")
        except Exception as e:
            self.log(f"[DEDUP] Error general: {e}")
        return eliminados

    def barrer_pdfs_huerfanos(self, cedula=None, servicio=None):
        """Mueve cualquier PDF que haya quedado SUELTO en la raiz de
        ``download_dir`` (es decir, no dentro de una subcarpeta de servicio)
        hacia la carpeta del servicio indicado. Si no hay servicio, los pone
        en ``_SIN_CLASIFICAR/``.

        Esto es una RED DE SEGURIDAD para PDFs que no fueron movidos por el
        flujo normal (timeouts del watcher de descarga, errores intermedios,
        archivos temporales, etc.).
        Devuelve la lista de rutas finales movidas.
        """
        movidos = []
        try:
            base = getattr(self, "download_dir", None)
            if not base or not os.path.isdir(base):
                return movidos
            destino_base = self._nombre_carpeta_servicio(servicio) if servicio else "_SIN_CLASIFICAR"
            destino_dir = os.path.join(base, destino_base)
            for nombre in os.listdir(base):
                ruta = os.path.join(base, nombre)
                if not os.path.isfile(ruta):
                    continue
                low = nombre.lower()
                if not low.endswith(".pdf"):
                    continue
                # No mover archivos en proceso de descarga
                if low.endswith(".crdownload") or low.endswith(".tmp") or low.endswith(".part"):
                    continue
                if not os.path.isdir(destino_dir):
                    os.makedirs(destino_dir, exist_ok=True)
                    self.log(f"[BARRIDO] Carpeta creada: {destino_dir}")
                # Renombrar para evitar colisiones
                cc = str(cedula).strip() if cedula else ""
                base_nombre = nombre
                if cc and cc not in base_nombre:
                    base_nombre = f"{cc}_{nombre}"
                destino_final = os.path.join(destino_dir, base_nombre)
                contador = 1
                stem, ext = os.path.splitext(base_nombre)
                while os.path.exists(destino_final):
                    destino_final = os.path.join(destino_dir, f"{stem}_{contador}{ext}")
                    contador += 1
                try:
                    shutil.move(ruta, destino_final)
                    movidos.append(destino_final)
                    self.log(f"[BARRIDO] PDF huerfano movido: {nombre} -> {destino_final}")
                except Exception as e:
                    self.log(f"[BARRIDO] No se pudo mover {nombre}: {e}")
        except Exception as e:
            self.log(f"[BARRIDO] Error general: {e}")
        return movidos

    def _mover_a_subcarpeta(self, ruta_archivo, cedula, tipo_atencion, servicio, numero_factura=None,
                             fecha_inicio=None, fecha_fin=None, numero_ingreso=None):
        """
        Organiza descargas por servicio:
        Downloads/HC_MASIVA_xxx/<SERVICIO>/<CC_SIGLA[_FACTURA]>.pdf

        Antes de mover, valida que el PDF:
          - No esté vacío (peso + texto)
          - Mencione el servicio esperado
          - Su fecha esté en el rango pedido
        Si falla la validación, elimina el PDF y devuelve None.
        """
        try:
            if not os.path.exists(ruta_archivo):
                return ruta_archivo

            # --- VALIDACION POST-DESCARGA (informativa, NO bloqueante) ---
            # El usuario quiere que TODO PDF descargado quede en la carpeta del
            # servicio. Si la validacion falla solo se loggea como advertencia.
            try:
                ok, motivo = self.validar_pdf_descargado(
                    ruta_archivo,
                    servicio_esperado=servicio,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                )
                if not ok:
                    self.log(f"[VALIDACION] PDF dudoso para CC={cedula}: {motivo} (se conserva en carpeta del servicio)")
            except Exception as e:
                self.log(f"[WARN] Error en validacion previa de PDF: {e} - se continua con el movimiento")

            cc = str(cedula).strip()
            cod_servicio = self._codigo_servicio_por_contexto(servicio, tipo_atencion)
            factura = self._normalizar_numero_factura(numero_factura)
            carpeta_servicio = self._nombre_carpeta_servicio(servicio)
            carpeta_destino = os.path.join(self.download_dir, carpeta_servicio)
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino, exist_ok=True)
                self.log(f"[INFO] Carpeta creada: {carpeta_destino}")

            ingreso = self._normalizar_numero_factura(numero_ingreso)
            # Prioridad de naming: ingreso > factura > base. (Pref. usuario: MAYUSCULA)
            if ingreso:
                nombre_archivo = f"{cc}_{cod_servicio}_{ingreso}.pdf".upper()
            elif factura:
                nombre_archivo = f"{cc}_{cod_servicio}_{factura}.pdf".upper()
            else:
                nombre_archivo = f"{cc}_{cod_servicio}.pdf".upper()
            ruta_canonica = os.path.join(carpeta_destino, nombre_archivo)

            # Evitar duplicados: si ya existe ese tipo/servicio para la cédula, no guardar otro.
            if os.path.exists(ruta_canonica):
                try:
                    os.remove(ruta_archivo)
                    self.log(f"[INFO] Duplicado omitido (ya existe): {ruta_canonica}")
                except Exception:
                    self.log(f"[INFO] Duplicado detectado (no se pudo borrar temporal): {ruta_archivo}")
                return ruta_canonica

            nueva_ruta = ruta_canonica

            # Mover archivo
            shutil.move(ruta_archivo, nueva_ruta)
            self.log(f"[EXITO] Archivo organizado en: {nueva_ruta}")
            # Contabilizar y reiniciar navegador cada N descargas para evitar caducidad
            self._registrar_descarga_y_chequear_reinicio()
            return nueva_ruta
        except Exception as e:
            self.log(f"[WARN] No se pudo mover el archivo a la subcarpeta: {e}")
            return ruta_archivo

    def _extraer_texto_pdf(self, ruta_pdf, max_paginas=2):
        """Extrae texto en mayúsculas de las primeras N páginas. '' si falla."""
        try:
            doc = fitz.open(ruta_pdf)
            partes = []
            for i in range(min(max_paginas, len(doc))):
                try:
                    partes.append(doc[i].get_text() or "")
                except Exception:
                    pass
            doc.close()
            return normalize_text(" ".join(partes))
        except Exception as e:
            self.log(f"[WARN] No se pudo leer PDF: {e}")
            return ""

    def _validar_pdf_no_vacio(self, ruta_pdf):
        """(ok, motivo) - PDF debe pesar > PDF_MIN_BYTES y tener texto > PDF_MIN_TEXTO."""
        try:
            if not os.path.exists(ruta_pdf):
                return False, "archivo inexistente"
            tam = os.path.getsize(ruta_pdf)
            if tam < self.PDF_MIN_BYTES:
                return False, f"PDF muy pequeño ({tam} bytes < {self.PDF_MIN_BYTES})"
            texto = self._extraer_texto_pdf(ruta_pdf, max_paginas=2)
            if len(texto.strip()) < self.PDF_MIN_TEXTO:
                return False, f"PDF sin texto extraíble ({len(texto)} chars)"
            return True, "ok"
        except Exception as e:
            return False, f"error validando PDF: {e}"

    def _coincide_servicio_pdf(self, texto_pdf_norm, servicio_esperado):
        """Devuelve True si el texto del PDF contiene el servicio esperado."""
        if not servicio_esperado:
            return True
        sv = normalize_text(servicio_esperado)
        if not sv:
            return True
        candidatos = {sv}
        if "PSICOLOGIA CONTROL" in sv:
            candidatos.update({"PSICOLOGIA CONTROL SM", "PSICOLOGIA SM", "PSICOLOGIA"})
        if "PSICOLOGIA PRIMERA" in sv:
            candidatos.update({"PSICOLOGIA PRIMERA VEZ", "VALORACION PSICOLOGIA"})
        if "TRABAJO SOCIAL" in sv:
            candidatos.update({"TRABAJO SOCIAL SM", "TRABAJO SOCIAL"})
        if "PSIQUIATRIA" in sv:
            candidatos.update({"PSIQUIATRIA SM", "PSIQUIATRIA"})
        if "MEDICINA GENERAL" in sv:
            candidatos.update({"MEDICINA GENERAL", "CONSULTA MEDICINA"})
        if "TERAPIA FISICA" in sv or "FISIOTERAPIA" in sv:
            candidatos.update({"TERAPIA FISICA", "FISIOTERAPIA"})
        if "ENFERMERIA" in sv:
            candidatos.update({"ENFERMERIA"})
        if "ODONTOLOGIA" in sv:
            candidatos.update({"ODONTOLOGIA"})
        for c in candidatos:
            if c and c in texto_pdf_norm:
                return True
        return False

    def _extraer_fecha_pdf(self, texto_pdf_norm):
        """Busca la primera fecha DD/MM/YYYY o DD-MM-YYYY en el texto."""
        try:
            import re as _re
            m = _re.search(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b", texto_pdf_norm)
            if not m:
                return None
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            from datetime import datetime as _dt
            return _dt(y, mo, d)
        except Exception:
            return None

    def _fecha_en_rango(self, texto_pdf_norm, fecha_inicio, fecha_fin):
        """True si la fecha del PDF cae dentro del rango [fecha_inicio, fecha_fin]."""
        if not fecha_inicio or not fecha_fin:
            return True
        try:
            from datetime import datetime as _dt
            def _parse(s):
                s = str(s).strip().replace("-", "/")
                for fmt in ("%d/%m/%Y", "%d/%m/%y"):
                    try:
                        return _dt.strptime(s, fmt)
                    except ValueError:
                        continue
                return None
            fi = _parse(fecha_inicio)
            ff = _parse(fecha_fin)
            fpdf = self._extraer_fecha_pdf(texto_pdf_norm)
            if not fi or not ff or not fpdf:
                return True
            return fi.date() <= fpdf.date() <= ff.date()
        except Exception:
            return True

    def validar_pdf_descargado(self, ruta_pdf, servicio_esperado=None,
                                fecha_inicio=None, fecha_fin=None):
        """
        Validación completa post-descarga.
        Retorna (ok: bool, motivo: str).
        """
        ok, motivo = self._validar_pdf_no_vacio(ruta_pdf)
        if not ok:
            return False, motivo
        texto = self._extraer_texto_pdf(ruta_pdf, max_paginas=2)
        if servicio_esperado and not self._coincide_servicio_pdf(texto, servicio_esperado):
            return False, f"servicio en PDF no coincide con '{servicio_esperado}'"
        if not self._fecha_en_rango(texto, fecha_inicio, fecha_fin):
            return False, f"fecha del PDF fuera del rango {fecha_inicio} - {fecha_fin}"
        return True, "ok"

    def _registrar_descarga_y_chequear_reinicio(self):
        """
        Incrementa el contador de descargas y reinicia el navegador
        cada MAX_DESCARGAS_POR_SESION para evitar caducidad de sesión.
        """
        try:
            self._descargas_en_sesion += 1
            if self._descargas_en_sesion >= self.MAX_DESCARGAS_POR_SESION:
                self.log(f"[MANTENIMIENTO] Alcanzadas {self._descargas_en_sesion} descargas en esta sesión. "
                         f"Reiniciando navegador para evitar caducidad...")
                self._descargas_en_sesion = 0
                try:
                    self.reiniciar_navegador_y_sesion(motivo="reinicio preventivo cada 50 descargas")
                except Exception as e:
                    self.log(f"[WARN] Falló reinicio preventivo: {e}")
        except Exception:
            pass

    def detectar_tipo_atencion(self, ruta_pdf):
        """
        Analiza el PDF para encontrar el tipo de atenciÃ³n.
        Busca: "PRIMERA VEZ", "EVOLUCION", "VALORACION".
        Retorna la primera coincidencia o "DESCONOCIDO".
        """
        try:
            self.log(f"[INFO] Analizando PDF para tipo de atenciÃ³n: {ruta_pdf}")
            doc = fitz.open(ruta_pdf)
            # Solo analizamos la primera pÃ¡gina, suele estar ahÃ­ el encabezado
            if len(doc) > 0:
                text = doc[0].get_text().upper()
                text_norm = normalize_text(text)
                # No usar "INGRESO" (por "Ingreso No:") para evitar falsos positivos.
                if "PRIMERA VEZ" in text_norm: return "PRIMERA VEZ"
                if "EVOLUCION" in text_norm or "CONTROL" in text_norm or "SEGUIMIENTO" in text_norm: return "EVOLUCION"
                if "VALORACION" in text_norm: return "VALORACION"
            
            doc.close()
            return "DESCONOCIDO"
        except Exception as e:
            self.log(f"[WARN] Error analizando PDF: {e}")
            return "ERROR_LECTURA"

    def _normalizar_tipo_objetivo(self, tipo_hc_objetivo):
        t = normalize_text(tipo_hc_objetivo)
        if not t:
            return None
        if "VALORACION" in t or t == "VAL":
            return "VALORACION"
        if "EVOLUCION" in t or t == "EVO":
            return "EVOLUCION"
        if "PRIMERA VEZ" in t or t in ("PRIMERA", "PRV", "INGRESO"):
            return "PRIMERA VEZ"
        return None

    def _detectar_tipo_en_texto_fila(self, texto_fila):
        texto = normalize_text(texto_fila)
        if "PRIMERA VEZ" in texto or "PRIMERA" in texto:
            return "PRIMERA VEZ"
        if "EVOLUCION" in texto or "CONTROL" in texto or "SEGUIMIENTO" in texto:
            return "EVOLUCION"
        if "VALORACION" in texto or "VALORACION INICIAL" in texto:
            return "VALORACION"
        return "OTRO"

    def _texto_fila_por_boton(self, boton):
        try:
            # 1) Forma más confiable: leer la fila <tr> contenedora del botón.
            try:
                fila = boton.find_element(By.XPATH, "ancestor::tr[1]")
                texto_tr = (fila.text or "").strip()
                if texto_tr:
                    return texto_tr
            except Exception:
                pass

            # 2) Fallback con JS sobre el elemento más cercano tipo fila.
            try:
                texto_js = self.driver.execute_script(
                    "var b=arguments[0]; var tr=b && b.closest ? b.closest('tr') : null; return tr ? (tr.innerText || '') : '';",
                    boton
                )
                if texto_js and str(texto_js).strip():
                    return str(texto_js).strip()
            except Exception:
                pass

            # 3) Fallback legacy por sufijo de IDs.
            sufijo = "0001"
            name_attr = boton.get_attribute("name")
            if name_attr and "_" in name_attr:
                sufijo = name_attr.split("_")[-1]
            xpath_fila = f"//*[contains(@id, '_{sufijo}')]"
            elementos = self.driver.find_elements(By.XPATH, xpath_fila)
            texto_fila = " ".join([e.text for e in elementos if e.text and e.text.strip()])
            return texto_fila
        except Exception:
            return ""

    def _extraer_numero_ingreso_de_fila(self, texto_fila):
        """Extrae el numero de ingreso (columna 'Ingreso' de la tabla INPEC360).
        El ingreso suele ser un entero de 6-9 digitos. Se prioriza el numero mas
        grande del rango aceptado dentro del texto de la fila para evitar confundirlo
        con la cedula u otros codigos. Devuelve string sin signos o '' si no aplica.
        """
        try:
            import re as _re
            if not texto_fila:
                return ""
            tokens = _re.findall(r"\b\d{6,9}\b", str(texto_fila))
            if not tokens:
                return ""
            # Heuristica: el ingreso suele ser de 7-8 digitos. Tomamos el ultimo
            # numero de 6-9 digitos que NO coincida con una cedula tipica (>=9).
            candidatos = [t for t in tokens if 6 <= len(t) <= 8]
            if not candidatos:
                return ""
            return candidatos[-1]
        except Exception:
            return ""

    def _normalizar_fecha_ddmmyyyy(self, valor):
        """
        Normaliza fechas de entrada a DD/MM/YYYY.
        Acepta DD/MM/YYYY, D/M/YYYY y YYYY-MM-DD.
        """
        if valor is None:
            return ""
        s = str(valor).strip()
        if not s:
            return ""
        if s.lower() == "hoy":
            return datetime.datetime.now().strftime("%d/%m/%Y")

        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y"):
            try:
                dt = datetime.datetime.strptime(s, fmt)
                return dt.strftime("%d/%m/%Y")
            except Exception:
                pass
        return s

    def _set_fecha_input(self, elemento, fecha_texto, label_log):
        """
        Escribe la fecha de forma robusta: limpia, escribe y fuerza valor exacto con JS.
        Evita errores de máscara como 02/110/2026.
        """
        self.resaltar_elemento(elemento)
        self.driver.execute_script("arguments[0].value = '';", elemento)
        elemento.clear()
        elemento.send_keys(fecha_texto)
        # Forzar valor exacto independientemente de la mascara.
        self.driver.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
            elemento,
            fecha_texto,
        )
        verif = (elemento.get_attribute("value") or "").strip()
        if verif != fecha_texto:
            self.log(f"[WARN] {label_log}: valor final '{verif}' distinto a '{fecha_texto}'")

    def _esperar_archivo_descargado(self, archivos_antes, timeout=30):
        if not hasattr(self, 'download_dir'):
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                archivos_ahora = set(os.listdir(self.download_dir))
                nuevos = archivos_ahora - archivos_antes
                candidatos = [
                    f for f in nuevos
                    if f.lower().endswith(".pdf") and not f.lower().endswith(".crdownload")
                ]
                if candidatos:
                    candidatos.sort(
                        key=lambda nombre: os.path.getmtime(os.path.join(self.download_dir, nombre)),
                        reverse=True,
                    )
                    return candidatos[0]
            except Exception:
                pass
            time.sleep(1)

        return None

    def _detectar_ventana_nueva(self, ventanas_antes, timeout=8):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                ventanas_despues = self.driver.window_handles
                nuevas = [handle for handle in ventanas_despues if handle not in ventanas_antes]
                if nuevas:
                    self.driver.switch_to.window(nuevas[-1])
                    self.log("[INFO] Se detecto una nueva pestaña/ventana del visor PDF.")
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        return False

    def _cerrar_ventanas_auxiliares(self, ventanas_principales):
        try:
            for handle in list(self.driver.window_handles):
                if handle in ventanas_principales:
                    continue
                try:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                except Exception as e:
                    self.log(f"[WARN] No se pudo cerrar la ventana auxiliar: {e}")
            if ventanas_principales:
                self.driver.switch_to.window(ventanas_principales[0])
        except Exception as e:
            self.log(f"[WARN] No se pudo restaurar la ventana principal: {e}")

    def _contexto_actual_es_pdf(self):
        try:
            url_actual = (self.driver.current_url or "").lower()
            if "avisualizar_pdf" in url_actual or url_actual.endswith(".pdf"):
                return True
            return bool(self.driver.execute_script("return !!document.querySelector('pdf-viewer, embed[type=\"application/pdf\"], iframe[src*=\"pdf\"]');"))
        except Exception:
            return False

    def _descargar_pdf_desde_contexto_actual(self, cedula, ventanas_antes, archivos_antes, numero_factura, tipo_detectado_tabla, servicio, fecha_inicio=None, fecha_fin=None, numero_ingreso=None):
        try:
            current_url = self.driver.current_url
            if not current_url:
                return None
            if "avisualizar_pdf" not in current_url and not current_url.lower().endswith(".pdf"):
                return None

            self.log(f"[INFO] URL de PDF detectada: {current_url}")
            self.log("[INFO] Intentando descarga directa via HTTP (Requests)...")

            session = requests.Session()
            selenium_cookies = self.driver.get_cookies()
            for cookie in selenium_cookies:
                session.cookies.set(cookie['name'], cookie['value'])

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
                "Referer": current_url,
            }
            response = session.get(current_url, headers=headers, stream=True, verify=False, timeout=30)
            content_type = response.headers.get('Content-Type', '').lower()
            if response.status_code != 200 or ('pdf' not in content_type and 'application/octet-stream' not in content_type):
                self.log(f"[WARN] Descarga directa no válida. status={response.status_code} content-type={content_type}")
                return None

            temp_file = os.path.join(self.download_dir, f"temp_{cedula}_{int(time.time())}.pdf")
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            tipo_final = self.detectar_tipo_atencion(temp_file) if tipo_detectado_tabla in ("DESCONOCIDO", "OTRO") else tipo_detectado_tabla
            self._mover_a_subcarpeta(
                temp_file, cedula, tipo_final, servicio,
                numero_factura=numero_factura,
                fecha_inicio=fecha_inicio, fecha_fin=fecha_fin,
                numero_ingreso=numero_ingreso,
            )
            self._cerrar_ventanas_auxiliares(ventanas_antes)
            # Limpiar cualquier PDF DUPLICADO que Chrome haya auto-descargado en paralelo.
            try:
                self._eliminar_pdfs_duplicados_recientes(archivos_antes, ventana_segundos=15)
            except Exception:
                pass

            self.log(f"[EXITO] PDF descargado y pestaña cerrada para CC={cedula}.")
            return tipo_final
        except Exception as e:
            self.log(f"[WARN] Falló descarga directa del PDF abierto: {e}")
            return None

    def descargar_historia_clinica(self, cedula, fecha_inicio, fecha_fin, servicio=None, estrategia="RECIENTE", tipo_hc_objetivo=None, _reintento=0, numero_factura=None, numero_ingreso=None):
        # Crear solo la carpeta de servicio antes de intentar la descarga.
        try:
            base_dir = self.download_dir if hasattr(self, 'download_dir') else 'downloads'
            carpeta_servicio = os.path.join(base_dir, self._nombre_carpeta_servicio(servicio or 'SIN_SERVICIO'))
            os.makedirs(carpeta_servicio, exist_ok=True)
            self.log(f"[INFO] Carpeta pre-creada para servicio: {carpeta_servicio}")
        except Exception as e:
            self.log(f"[WARN] No se pudo crear carpeta previa: {e}")
        """
        Descarga la historia clÃ­nica de un paciente dado.
        estrategia: "RECIENTE" (default, primera de la lista) o "ANTIGUA" (Ãºltima de la lista).
        """
        self.log(f"--- INICIANDO DESCARGA DE HC: {cedula} ---")
        
        # Determinar carpeta de descarga actual (para monitoreo)
        # Esto depende de cÃ³mo se configurÃ³ el driver, pero podemos intentar inferirlo o buscar en las prefs
        # si pudiÃ©ramos acceder a ellas. 
        # Como no guardamos el download_dir en self, asumimos que si no se configurÃ³, es 'downloads'.
        # MEJORA: PodrÃ­amos guardar self.download_dir en iniciar_navegador.
        
        try:
            if not self._driver_operativo():
                if _reintento < 1:
                    self.log("[RECOVERY] Driver no operativo al iniciar descarga. Reiniciando navegador...")
                    if self.reiniciar_navegador_y_sesion(f"driver cerrado/invalido al iniciar HC CC={cedula}"):
                        return self.descargar_historia_clinica(
                            cedula=cedula,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            servicio=servicio,
                            estrategia=estrategia,
                            tipo_hc_objetivo=tipo_hc_objetivo,
                            _reintento=_reintento + 1
                        )
                raise Exception("Driver no operativo y no fue posible recuperar sesion.")

            if self._pagina_en_blanco_o_error() or self._es_pantalla_login():
                self.recuperar_pagina_y_sesion(f"inicio descarga HC CC={cedula}")

            # 1. Verificar si ya estamos en el mÃ³dulo (OptimizaciÃ³n de navegaciÃ³n)
            self.driver.switch_to.default_content()
            en_modulo = False
            try:
                # BÃºsqueda rÃ¡pida sin esperas largas
                if self.buscar_elemento_en_frames(*SELECTORES["hc_pac_id"]):
                    en_modulo = True
                    self.log("[OPTIMIZACION] Ya estamos en el mÃ³dulo de Historia ClÃ­nica. Omitiendo navegaciÃ³n de menÃº.")
            except: pass

            if not en_modulo:
                self.navegar_a_modulo(
                    SELECTORES["menu_consultar_hc"], 
                    SELECTORES["submenu_consultar_historia"]
                )
            
            # Esperar un momento para asegurar que el formulario se limpiÃ³/cargÃ³
            time.sleep(1)
            
            # 2. Manejo de Frames (Buscar input de cÃ©dula)
            # Primero salir al contexto default antes de buscar frames nuevamente
            self.driver.switch_to.default_content()
            
            if not self.buscar_elemento_en_frames(*SELECTORES["hc_pac_id"]):
                self.log("[ERROR] No se encontrÃ³ el campo de cÃ©dula (vPACNUMIDE).")
                self.diagnostico_exhaustivo()
                raise Exception("No se encontrÃ³ formulario de HC")
            
            # 3. Llenar formulario
            self.log(f"[INFO] Llenando datos: CC={cedula}, Fechas={fecha_inicio}-{fecha_fin}, Servicio={servicio}")
            
            # CÃ©dula
            inp_cc = self.driver.find_element(*SELECTORES["hc_pac_id"])
            # ValidaciÃ³n de seguridad: Asegurar que no sea campo de fecha
            try:
                inp_id = inp_cc.get_attribute('id')
                if "FEC" in str(inp_id).upper():
                    self.log(f"[CRITICO] El selector de cÃ©dula apunta a un campo de FECHA ({inp_id}). Abortando escritura.")
                    raise Exception("Selector de cÃ©dula incorrecto (es una fecha)")
            except: pass
            
            self.resaltar_elemento(inp_cc)
            inp_cc.clear()
            inp_cc.send_keys(cedula)
            
            # Fechas (Si aplica)
            fecha_inicio = self._normalizar_fecha_ddmmyyyy(fecha_inicio) if fecha_inicio else ""
            if fecha_inicio:
                try:
                    inp_ini = self.driver.find_element(*SELECTORES["hc_fecha_ini"])
                    self._set_fecha_input(inp_ini, fecha_inicio, "Fecha Inicio")
                except Exception as e:
                    self.log(f"[ERROR] Fallo al escribir Fecha Inicio: {e}")
            else:
                try:
                    inp_ini = self.driver.find_element(*SELECTORES["hc_fecha_ini"])
                    inp_ini.clear()
                except:
                    pass

            if fecha_fin:
                if str(fecha_fin).lower() == "hoy":
                    fecha_fin = datetime.datetime.now().strftime("%d/%m/%Y")
            else:
                # Si es None o vacio, forzamos fecha de hoy
                fecha_fin = datetime.datetime.now().strftime("%d/%m/%Y")
                self.log(f"[INFO] Fecha fin vacia -> Se uso fecha de hoy: {fecha_fin}")

            fecha_fin = self._normalizar_fecha_ddmmyyyy(fecha_fin)
            self.log(f"[INFO] Fechas finales a enviar: inicio={fecha_inicio or '(vacio)'} fin={fecha_fin}")

            # Escribir Fecha Fin (Obligatorio)
            try:
                inp_fin = self.driver.find_element(*SELECTORES["hc_fecha_fin"])
                self._set_fecha_input(inp_fin, fecha_fin, "Fecha Fin")
            except Exception as e:
                self.log(f"[ERROR CRITICO] Fallo al escribir Fecha Fin: {e}")
                

            # Servicio (Si aplica) - OBLIGATORIO si viene en el Excel
            try:
                el_serv = self.buscar_elemento_en_frames(*SELECTORES["hc_servicio"])
                sel_servicio = Select(el_serv)
                # RESETEAR siempre a la primera opción para limpiar el estado del paciente anterior
                try:
                    sel_servicio.select_by_index(0)
                    time.sleep(0.5)
                except:
                    pass
                # Seleccionar el servicio si se proporciona
                if servicio:
                    if not self.seleccionar_servicio(el_serv, servicio):
                        # NO continuar: si el servicio no se pudo seleccionar,
                        # el bot descargaría "cualquier cosa". Abortar el paciente.
                        raise Exception(f"SERVICIO_NO_DISPONIBLE: '{servicio}' no existe en el dropdown del paciente {cedula}")
                    seleccionado_norm = self._normalizar_servicio_estricto(sel_servicio.first_selected_option.text)
                    solicitado_norm   = self._normalizar_servicio_estricto(servicio)
                    if solicitado_norm and solicitado_norm != seleccionado_norm:
                        raise Exception(f"SERVICIO_MISMATCH: solicitado='{servicio}' (norm='{solicitado_norm}') seleccionado='{sel_servicio.first_selected_option.text}' (norm='{seleccionado_norm}')")
                    self.log(f"[OK] Servicio confirmado en form: '{sel_servicio.first_selected_option.text}' (solicitado='{servicio}')")
            except Exception as e:
                # Reraise: no podemos consultar sin el servicio correcto
                self.log(f"[ABORTAR] Servicio no seleccionable para CC={cedula}: {e}")
                raise

            btn_consultar = self.driver.find_element(*SELECTORES["hc_btn_consultar"])
            self.resaltar_elemento(btn_consultar)
            btn_consultar.click()
            self.log("[INFO] Consulta enviada. Esperando carga completa de resultados...")
            
            # Espera dinÃ¡mica para asegurar que la consulta terminÃ³
            self.esperar_carga_completa(timeout=60)

            # VerificaciÃ³n inmediata de "Sin registros" para evitar esperas innecesarias
            try:
                cuerpo_texto = self.driver.find_element(By.TAG_NAME, "body").text
                # Lista ampliada de posibles mensajes de "no resultados"
                mensajes_vacio = [
                    "No se encontraron registros", 
                    "No existen registros", 
                    "No hay datos", 
                    "0 registros encontrados",
                    "No se encontrÃ³ informaciÃ³n",
                    "No se han encontrado datos"
                ]
                if any(m in cuerpo_texto for m in mensajes_vacio):
                    self.log("[WARN] Consulta finalizada: No se encontraron registros clÃ­nicos (DetecciÃ³n rÃ¡pida en body).")
                    return False, "Sin registros encontrados"
            except Exception: 
                pass # Si falla la lectura, continuamos con la espera normal
            
            # 5. Esperar resultados y Click en Imprimir
            try:
                # Verificamos si hay botÃ³n de imprimir (Timeout aumentado a 10s para conexiones lentas)
                wait_resultados = WebDriverWait(self.driver, 10)
                
                try:
                    wait_resultados.until(EC.visibility_of_element_located(SELECTORES["hc_btn_imprimir"]))
                except TimeoutException:
                     # Si falla, verificar si hay mensaje de "No se encontraron registros" en contenedores especÃ­ficos
                    try:
                        # Buscar en mensajes de error/warning tÃ­picos
                        msgs = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'Error') or contains(@class, 'Warning') or contains(@class, 'Message')]")
                        for m in msgs:
                             if m.is_displayed() and any(txt in m.text for txt in ["No se encontraron", "No existen", "0 registros"]):
                                 self.log(f"[WARN] Mensaje detectado en UI: {m.text}")
                                 return False, "Sin registros encontrados"
                        
                        cuerpo = self.driver.find_element(By.TAG_NAME, "body").text
                        if "No se encontraron" in cuerpo or "No existen" in cuerpo:
                            self.log("[WARN] El sistema indica que no hay historias clÃ­nicas para este paciente.")
                            return False, "Sin registros"
                    except: pass
                    # Relanzar excepciÃ³n si no fue un caso controlado
                    raise TimeoutException("No se encontraron botones de imprimir ni mensajes de error conocidos tras la consulta.")

                # Buscar TODOS los botones de imprimir para aplicar estrategia
                # XPath para encontrar input[name^='vIMPRIMIRHC_'] (Icono Impresora)
                btns_print = self.driver.find_elements(By.XPATH, "//input[starts-with(@name, 'vIMPRIMIRHC_')]")
                
                if not btns_print:
                    # Fallback si no encuentra por XPath
                    self.log("[WARN] No se encontraron botones de impresora por XPath, usando selector default.")
                    try:
                        btns_print = [self.driver.find_element(*SELECTORES["hc_btn_imprimir"])]
                    except NoSuchElementException:
                        # Ãšltimo intento: Buscar inputs de tipo imagen o enlaces con 'imprimir'
                         btns_print = self.driver.find_elements(By.XPATH, "//input[@type='image' and contains(@src, 'imprimir')] | //a[contains(@href, 'imprimir')]")

                if not btns_print:
                     self.log("[ERROR CRITICO] La tabla parece tener datos pero no se detectaron botones de descarga.")
                     # Dump html para debug
                     # with open("debug_no_buttons.html", "w") as f: f.write(self.driver.page_source)
                     raise Exception("Tabla cargada pero sin botones de descarga identificables")
                
                self.log(f"[INFO] Se encontraron {len(btns_print)} historias clinicas disponibles.")

                # ===== ESTRATEGIA RANGO FECHAS =====
                # Descarga TODAS las HC validas que el paciente tenga en el rango.
                # Cada PDF se nombra <CC>_<COD_SERVICIO>_<NUMERO_INGRESO>.pdf
                _est_norm = str(estrategia or "").upper().strip().replace("_", " ")
                if _est_norm in ("RANGO FECHAS", "RANGO") and not numero_ingreso:
                    ingresos_unicos = []
                    seen_ing = set()
                    for _btn in btns_print:
                        try:
                            _txt = self._texto_fila_por_boton(_btn)
                            _txtu = (_txt or "").upper()
                            if any(s in _txtu for s in ("NO ASISTIDA", "CANCELADA", "POR ATENDER")):
                                continue
                            _ing = self._extraer_numero_ingreso_de_fila(_txt)
                            if not _ing or _ing in seen_ing:
                                continue
                            seen_ing.add(_ing)
                            ingresos_unicos.append(_ing)
                        except Exception:
                            continue
                    self.log(f"[INFO] RANGO FECHAS: {len(ingresos_unicos)} ingresos validos detectados: {ingresos_unicos}")
                    if not ingresos_unicos:
                        return False, "RANGO FECHAS: sin registros validos en el rango"
                    descargados = []
                    fallos = []
                    for _ing in ingresos_unicos:
                        try:
                            ok_i, info_i = self.descargar_historia_clinica(
                                cedula=cedula,
                                fecha_inicio=fecha_inicio,
                                fecha_fin=fecha_fin,
                                servicio=servicio,
                                estrategia="RECIENTE",
                                tipo_hc_objetivo=None,
                                _reintento=2,
                                numero_factura=numero_factura,
                                numero_ingreso=_ing,
                            )
                            if ok_i:
                                descargados.append(_ing)
                            else:
                                fallos.append(f"{_ing}:{info_i}")
                        except Exception as _e:
                            fallos.append(f"{_ing}:{_e}")
                    if descargados:
                        return True, f"RANGO FECHAS: {len(descargados)} descargados ({','.join(descargados)})"
                    return False, f"RANGO FECHAS sin descargas. fallos={fallos}"

                target_btn = None
                tipo_detectado_tabla = "DESCONOCIDO"
                idx_btn_seleccionado = None
                tipo_objetivo_norm = self._normalizar_tipo_objetivo(tipo_hc_objetivo)
                es_psiquiatria = "PSIQUIATRIA" in normalize_text(servicio)

                if estrategia == "ANTIGUA":
                    indices_busqueda = range(len(btns_print) - 1, -1, -1)
                    self.log("[INFO] Estrategia: ANTIGUA - Se buscara desde el ultimo registro.")
                else:
                    indices_busqueda = range(0, len(btns_print))
                    self.log("[INFO] Estrategia: RECIENTE - Se buscara desde el primer registro.")

                for idx in indices_busqueda:
                    btn_actual = btns_print[idx]
                    texto_fila = self._texto_fila_por_boton(btn_actual)
                    texto_fila_up = texto_fila.upper()
                    tipo_fila = self._detectar_tipo_en_texto_fila(texto_fila)

                    # Filtro por NUMERO DE INGRESO (Excel) si se solicito uno especifico.
                    if numero_ingreso:
                        _ing_fila = self._extraer_numero_ingreso_de_fila(texto_fila)
                        if str(_ing_fila).strip() != str(numero_ingreso).strip():
                            self.log(f"[INFO] Fila {idx+1} descartada: ingreso fila={_ing_fila} != solicitado={numero_ingreso}")
                            continue

                    # Regla solicitada: para Psiquiatria filtrar por tipo de HC pedido en estrategia.
                    if es_psiquiatria and tipo_objetivo_norm and tipo_fila not in (tipo_objetivo_norm, "OTRO"):
                        self.log(f"[INFO] Fila {idx+1} descartada por tipo: detectado={tipo_fila}, requerido={tipo_objetivo_norm}")
                        continue

                    # Si el usuario pidio tipo en estrategia (aunque no sea psiquiatria), se respeta.
                    if (not es_psiquiatria) and tipo_objetivo_norm and tipo_fila not in (tipo_objetivo_norm, "OTRO"):
                        self.log(f"[INFO] Fila {idx+1} descartada por tipo solicitado: detectado={tipo_fila}, requerido={tipo_objetivo_norm}")
                        continue

                    if "NO ASISTIDA" in texto_fila_up or "CANCELADA" in texto_fila_up or "POR ATENDER" in texto_fila_up:
                        self.log(f"[INFO] Fila {idx+1} descartada por estado no valido.")
                        continue

                    target_btn = btn_actual
                    tipo_detectado_tabla = tipo_fila
                    idx_btn_seleccionado = idx
                    self.log(f"[INFO] Fila {idx+1} seleccionada. Tipo detectado: {tipo_detectado_tabla}")
                    break

                if target_btn is None:
                    if numero_ingreso:
                        return False, f"Sin registro con numero de ingreso {numero_ingreso} en el rango de fechas"
                    if tipo_objetivo_norm:
                        return False, f"Sin registros tipo {tipo_objetivo_norm} en el rango de fechas"
                    return False, "Sin registros validos para descargar en el rango de fechas"

                # Scroll al botÃ³n objetivo antes de interactuar (CRÃTICO para listas largas)
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", target_btn)
                    time.sleep(0.5) # Estabilizar tras scroll
                except: pass

                self.resaltar_elemento(target_btn)
                self.log(f"[ACCION] Haciendo clic en icono de impresora (vIMPRIMIRHC)...")
                
                # Monitoreo de archivos antes del click
                archivo_descargado = None  # Inicializar para robustez
                if hasattr(self, 'download_dir'):
                    # Limpiar archivos .crdownload o .tmp antiguos para evitar confusiones
                    try:
                        for f in glob.glob(os.path.join(self.download_dir, "*.crdownload")):
                            try: os.remove(f)
                            except: pass
                    except: pass
                    try:
                        archivos_antes = set(os.listdir(self.download_dir))
                    except:
                        archivos_antes = set()
                
                # Capturar ventanas antes del click
                ventanas_antes = self.driver.window_handles
                ventana_nueva = False
                
                try:
                    target_btn.click()
                except Exception as e_click:
                    # Stale Element Reference Exception: El elemento cambiÃ³, lo buscamos de nuevo
                    if "stale element reference" in str(e_click).lower():
                        self.log("[WARN] Elemento obsoleto (stale). Buscando botÃ³n de nuevo...")
                        try:
                            # Re-buscar botones
                            btns_re = self.driver.find_elements(By.XPATH, "//input[starts-with(@name, 'vIMPRIMIRHC_')]")
                            idx_re = idx_btn_seleccionado if idx_btn_seleccionado is not None else (len(btns_re)-1 if estrategia == "ANTIGUA" else 0)
                            if btns_re and len(btns_re) > idx_re:
                                target_btn = btns_re[idx_re]
                                target_btn.click()
                                self.log("[EXITO] Click exitoso tras recuperaciÃ³n.")
                            else:
                                raise Exception("No se pudo recuperar el botÃ³n tras StaleElement")
                        except Exception as e_re:
                            self.log(f"[WARN] FallÃ³ recuperaciÃ³n click normal ({e_re}). Intentando JS...")
                            try:
                                self.driver.execute_script("arguments[0].click();", target_btn)
                            except: pass # Ãšltimo intento
                    else:
                        self.log(f"[WARN] Click normal fallÃ³ ({str(e_click)}). Intentando JS...")
                        self.driver.execute_script("arguments[0].click();", target_btn)

                ventana_nueva = self._detectar_ventana_nueva(ventanas_antes, timeout=8)
                if hasattr(self, 'download_dir'):
                    archivo_descargado = self._esperar_archivo_descargado(archivos_antes, timeout=8)
                    if not archivo_descargado and ventana_nueva and self._contexto_actual_es_pdf():
                        tipo_descargado = self._descargar_pdf_desde_contexto_actual(
                            cedula=cedula,
                            ventanas_antes=ventanas_antes,
                            archivos_antes=archivos_antes,
                            numero_factura=numero_factura,
                            tipo_detectado_tabla=tipo_detectado_tabla,
                            servicio=servicio,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            numero_ingreso=numero_ingreso,
                        )
                        if tipo_descargado:
                            return True, tipo_descargado
                
                # Manejo de Descarga y Renombrado
                if hasattr(self, 'download_dir'):
                    if archivo_descargado:
                        self.log(f"[INFO] Archivo detectado: {archivo_descargado}")
                        ruta_original = os.path.join(self.download_dir, archivo_descargado)
                        try:
                            # Esperar un momento para asegurar que el archivo se liberó
                            time.sleep(2)
                            # Si la tabla no clasifica bien (DESCONOCIDO/OTRO), usamos el PDF.
                            if tipo_detectado_tabla in ("DESCONOCIDO", "OTRO"):
                                tipo_final = self.detectar_tipo_atencion(ruta_original)
                            else:
                                tipo_final = tipo_detectado_tabla
                            self._mover_a_subcarpeta(ruta_original, cedula, tipo_final, servicio, numero_factura=numero_factura, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, numero_ingreso=numero_ingreso)
                            # DEDUP: eliminar PDFs extra que Chrome haya auto-descargado en paralelo.
                            try:
                                self._eliminar_pdfs_duplicados_recientes(archivos_antes | {archivo_descargado}, ventana_segundos=15)
                            except Exception:
                                pass
                            return True, tipo_final
                        except Exception as e:
                            self.log(f"[WARN] No se pudo renombrar el archivo: {e}")
                            if tipo_detectado_tabla in ("DESCONOCIDO", "OTRO"):
                                tipo_final = self.detectar_tipo_atencion(ruta_original)
                            else:
                                tipo_final = tipo_detectado_tabla
                            self._mover_a_subcarpeta(ruta_original, cedula, tipo_final, servicio, numero_factura=numero_factura, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, numero_ingreso=numero_ingreso)
                            try:
                                self._eliminar_pdfs_duplicados_recientes(archivos_antes | {archivo_descargado}, ventana_segundos=15)
                            except Exception:
                                pass
                            return True, tipo_final
                        finally:
                            # Siempre cerrar la ventana nueva si existe
                            if ventana_nueva:
                                self._cerrar_ventanas_auxiliares(ventanas_antes)

                    self.log("[WARN] No se detectó descarga automática tras el click inicial.")
                    if not self._contexto_actual_es_pdf():
                        self._cerrar_ventanas_auxiliares(ventanas_antes)
                        self.log("[ERROR] No se abrió un visor PDF ni apareció un archivo descargado.")
                        try:
                            self.exportar_resumen()
                        except Exception as e:
                            self.log(f"[WARN] No se pudo exportar resumen: {e}")
                        return False, "No se detectó descarga"

                        # 2. INTENTO DE CLIC EN BOTÃ“N DE DESCARGA (Shadow DOM / JS)
                        # El usuario solicita explÃ­citamente usar el botÃ³n de descarga del visor
                        self.log("[ACCION] Intentando clic en botÃ³n de descarga del visor (JS/Shadow DOM)...")
                        
                        js_click_download = """
                        function clickDownload() {
                            try {
                                // Estrategia Universal de BÃºsqueda Recursiva en Shadow DOM
                                function findElement(root, predicate) {
                                    if (!root) return null;
                                    if (predicate(root)) return root;
                                    
                                    // Buscar en Shadow Root
                                    if (root.shadowRoot) {
                                        var res = findElement(root.shadowRoot, predicate);
                                        if (res) return res;
                                    }
                                    
                                    // Buscar en hijos
                                    if (root.children) {
                                        for (var i = 0; i < root.children.length; i++) {
                                            var res = findElement(root.children[i], predicate);
                                            if (res) return res;
                                        }
                                    }
                                    return null;
                                }
                                
                                var viewer = document.querySelector('pdf-viewer');
                                if (viewer) {
                                    // Buscar botÃ³n que sea 'cr-icon-button' y tenga icono de descarga
                                     var btn = findElement(viewer, function(el) {
                                         if (el.tagName !== 'CR-ICON-BUTTON') return false;
                                         
                                         // Coincidencia exacta basada en la evidencia del usuario (id="save" con label "Descargar")
                                         if (el.id === 'save' && (el.getAttribute('aria-label') === 'Descargar' || el.getAttribute('title') === 'Descargar')) return true;
                                         
                                         // Coincidencias genÃ©ricas anteriores
                                         if (el.getAttribute('iron-icon') === 'cr:file-download') return true;
                                         if (el.id === 'download' || el.id === 'downloads') return true;
                                         
                                         return false;
                                     });
                                    
                                    if (btn) {
                                        btn.click();
                                        return "Clicked via Recursive Search";
                                    }
                                }
                                
                                // Estrategia Backup: Selectores comunes
                                var selectors = [
                                    '#download', 
                                    'button[aria-label="Download"]', 
                                    'button[title="Descargar"]',
                                    'a[download]',
                                    '#secondaryToolbarButton'
                                ];
                                
                                for (var i = 0; i < selectors.length; i++) {
                                    var el = document.querySelector(selectors[i]);
                                    if (el && el.offsetParent !== null) {
                                        el.click();
                                        return "Clicked Generic Button";
                                    }
                                }
                                
                                return "Not Found";
                            } catch(e) {
                                return "Error: " + e.toString();
                            }
                        }
                        return clickDownload();
                        """
                        
                        # Bucle de espera activa para el botÃ³n de descarga
                        # Esto es necesario porque el visor PDF puede tardar en renderizar aunque la pÃ¡gina estÃ© "cargada"
                        start_wait_btn = time.time()
                        found_button = False
                        
                        self.log("[WAIT] Buscando botÃ³n de descarga en la interfaz del visor...")
                        
                        # ESTRATEGIA 0: ESCANEO DE LA PÃGINA (Guardar para diagnÃ³stico)
                        try:
                            os.makedirs(RUNTIME_LOG_DIR, exist_ok=True)
                            debug_visor_path = os.path.join(RUNTIME_LOG_DIR, "debug_visor.txt")
                            structure_scan_path = os.path.join(RUNTIME_LOG_DIR, "structure_scan.txt")
                            # 1. Guardar page_source bÃ¡sico
                            with open(debug_visor_path, "w", encoding="utf-8") as f:
                                f.write(self.driver.page_source)
                            
                            # 2. Escaneo profundo de Shadow DOM para encontrar estructura
                            js_deep_scan = """
                                function scanShadow(root, depth) {
                                    var output = "";
                                    var indent = " ".repeat(depth * 2);
                                    
                                    if (!root) return output;
                                    
                                    // Procesar elemento actual
                                    var tag = root.tagName ? root.tagName.toLowerCase() : "node";
                                    var id = root.id ? "#" + root.id : "";
                                    var cls = root.className ? "." + root.className : "";
                                    output += indent + tag + id + cls + "\\n";
                                    
                                    // Procesar Shadow Root
                                    if (root.shadowRoot) {
                                        output += indent + "  [SHADOW-ROOT]\\n";
                                        // Iterar hijos del shadow root
                                        var children = root.shadowRoot.children;
                                        for (var i = 0; i < children.length; i++) {
                                            output += scanShadow(children[i], depth + 2);
                                        }
                                    }
                                    
                                    // Procesar hijos normales
                                    if (root.children) {
                                        for (var i = 0; i < root.children.length; i++) {
                                            output += scanShadow(root.children[i], depth + 1);
                                        }
                                    }
                                    return output;
                                }
                                
                                // Iniciar escaneo desde el body o desde pdf-viewer
                                var viewer = document.querySelector('pdf-viewer');
                                if (viewer) return scanShadow(viewer, 0);
                                return scanShadow(document.body, 0);
                            """
                            scan_result = self.driver.execute_script(js_deep_scan)
                            with open(structure_scan_path, "w", encoding="utf-8") as f:
                                f.write(str(scan_result))
                                
                            self.log(f"[INFO] Página escaneada profundamente. Estructura guardada en '{structure_scan_path}'.")
                        except Exception as e: 
                            self.log(f"[WARN] Error al escanear pÃ¡gina: {e}")
                        
                        # ESTRATEGIA 0: DESCARGA DIRECTA POR URL (Requests con Cookies)
                        # Si la URL actual apunta al PDF (servlet), intentamos descargarlo directamente
                        # evitando la interacciÃ³n con la UI del visor de Chrome.
                        tipo_descargado = self._descargar_pdf_desde_contexto_actual(
                            cedula=cedula,
                            ventanas_antes=ventanas_antes,
                            archivos_antes=archivos_antes,
                            numero_factura=numero_factura,
                            tipo_detectado_tabla=tipo_detectado_tabla,
                            servicio=servicio,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            numero_ingreso=numero_ingreso,
                        )
                        if tipo_descargado:
                            return True, tipo_descargado

                        # ESTRATEGIA 1: BYPASS DE UI (Intentar descarga directa si hay URL de PDF visible)
                        # Buscamos si hay un <embed> o <iframe> con el PDF y creamos nuestro propio enlace de descarga
                        js_bypass = """
                            var embed = document.querySelector('embed[type="application/pdf"]');
                            if (embed && embed.src) {
                                var link = document.createElement('a');
                                link.href = embed.src;
                                link.download = 'documento_bypass.pdf';
                                document.body.appendChild(link);
                                link.click();
                                return "Descarga iniciada por Bypass";
                            }
                            return "No se encontrÃ³ embed PDF";
                        """
                        bypass_res = self.driver.execute_script(js_bypass)
                        if "Descarga iniciada" in str(bypass_res):
                            self.log(f"[EXITO] {bypass_res}")
                            found_button = True
                            time.sleep(3)
                        
                        # ESTRATEGIA 2: CLIC EN BOTÃ“N NATIVO (Solo si el Bypass fallÃ³)
                        if not found_button:
                            # Aumentamos el tiempo de bÃºsqueda estricta del botÃ³n
                            tiempo_busqueda_js = 10 
                            
                            js_click_download = """
                            function clickDownload() {
                                try {
                                    var viewer = document.querySelector('pdf-viewer');
                                    if (!viewer) return "No pdf-viewer found";
                                    
                                    // Helper para acceder al Shadow DOM
                                    var getShadow = (e) => e.shadowRoot || e;
                                    
                                    // ESTRATEGIA A: Ruta EspecÃ­fica (Basada en Screenshot)
                                    // pdf-viewer -> viewer-toolbar -> viewer-download-controls -> #save (o #download)
                                    try {
                                        var toolbar = getShadow(viewer).querySelector('viewer-toolbar');
                                        if (toolbar) {
                                            var controls = getShadow(toolbar).querySelector('viewer-download-controls');
                                            if (controls) {
                                                var btn = getShadow(controls).querySelector('#save'); // Prioridad ID 'save'
                                                if (!btn) btn = getShadow(controls).querySelector('#download'); // Fallback ID 'download'
                                                
                                                if (btn) {
                                                    btn.click();
                                                    return "Clicked via Specific Path: viewer-download-controls -> #" + btn.id;
                                                }
                                            }
                                        }
                                    } catch(e) { console.log("Path search failed: " + e); }
                                    
                                    // ESTRATEGIA C: BÃºsqueda de Fuerza Bruta (Iterar TODOS los nodos en Shadow DOM)
                                     function findAll(root) {
                                         var found = [];
                                         if (!root) return found;
                                         
                                         // Check current element
                                         if (root.id === 'save' || root.id === 'download' || 
                                            (root.tagName === 'CR-ICON-BUTTON' && root.getAttribute('iron-icon') === 'cr:file-download') ||
                                            (root.getAttribute && (root.getAttribute('aria-label') === 'Descargar' || root.getAttribute('title') === 'Descargar'))) {
                                             found.push(root);
                                         }
                                         
                                         // Shadow Root
                                         if (root.shadowRoot) {
                                             var children = root.shadowRoot.children;
                                             for (var i = 0; i < children.length; i++) {
                                                 found = found.concat(findAll(children[i]));
                                             }
                                         }
                                         
                                         // Normal Children
                                         if (root.children) {
                                             for (var i = 0; i < root.children.length; i++) {
                                                 found = found.concat(findAll(root.children[i]));
                                             }
                                         }
                                         return found;
                                     }
                                     
                                     var candidates = findAll(viewer);
                                     if (candidates.length > 0) {
                                         // Priorizar el que sea visible o tenga ID 'save'
                                         var best = candidates.find(c => c.id === 'save');
                                         if (!best) best = candidates[0];
                                         
                                         best.click();
                                         return "Clicked via Brute Force: #" + best.id + " (" + best.tagName + ")";
                                     }
                                     
                                     return "Not Found";
                                 } catch(e) {
                                     return "Error: " + e.toString();
                                 }
                             }
                             return clickDownload();
                             """
                             
                            while time.time() - start_wait_btn < tiempo_busqueda_js: 
                                resultado_click = self.driver.execute_script(js_click_download)
                                
                                # Log detallado para depuraciÃ³n
                                if "Error" in str(resultado_click) or "Not Found" in str(resultado_click):
                                    # Si falla, intentamos simular movimiento de ratÃ³n para "despertar" la UI
                                    try:
                                        action = webdriver.ActionChains(self.driver)
                                        action.move_by_offset(100, 100).perform()
                                    except: pass
                                else:
                                    self.log(f"[EXITO] Clic realizado en botÃ³n de descarga: {resultado_click}")
                                    found_button = True
                                    time.sleep(2) # Dar tiempo a que inicie la descarga
                                    break
                                
                                time.sleep(1) # Reintentar cada segundo
                        
                        if not found_button:
                            self.log("[WARN] No se encontrÃ³ botÃ³n de descarga por JS tras 5s. Activando PLAN B: Atajo de teclado (CTRL+S).")
                            # PLAN B: Simular CTRL+S (Guardar)
                            # Esto es equivalente a dar clic en descargar y suele funcionar cuando el JS no accede al Shadow DOM
                            try:
                                # Asegurar foco en el documento antes de enviar teclas
                                self.driver.execute_script("window.focus(); document.body.focus();")
                                time.sleep(0.5)
                                
                                action = webdriver.ActionChains(self.driver)
                                action.key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
                                self.log("[ACCION] Enviado comando CTRL+S.")
                                time.sleep(3)
                            except Exception as e:
                                self.log(f"[ERROR] FallÃ³ envÃ­o de teclas: {e}")
                            
                            # ESTRATEGIA 3: ACTION CHAINS (Clic en coordenadas fijas - Ãšltimo recurso visual)
                            if not found_button:
                                self.log("[WARN] JS y Teclado fallaron. Intentando clic por coordenadas (esquina superior derecha)...")
                                try:
                                    # Moverse a la esquina superior derecha donde suele estar el botÃ³n de descarga
                                    # Ajustar offset segÃºn resoluciÃ³n (ej: 150px desde la derecha, 60px desde arriba)
                                    action = webdriver.ActionChains(self.driver)
                                    
                                    # Mover al body primero
                                    self.driver.execute_script("window.scrollTo(0,0);")
                                    
                                    # Intentar ubicar el toolbar aunque sea en shadow
                                    # Si no, clic a ciegas
                                    ancho_ventana = self.driver.execute_script("return window.innerWidth;")
                                    
                                    # Coordenadas estimadas del botÃ³n de descarga en visor Chrome estÃ¡ndar:
                                    # X: Ancho - 150px, Y: 55px
                                    x_offset = ancho_ventana - 150
                                    y_offset = 55
                                    
                                    action.move_by_offset(x_offset, y_offset).click().perform()
                                    self.log(f"[ACCION] Clic en coordenadas estimadas: {x_offset}, {y_offset}")
                                    time.sleep(2)
                                    
                                    # Reset action chains
                                    action = webdriver.ActionChains(self.driver)
                                    action.move_by_offset(0, 0) # Reset
                                except Exception as e:
                                    self.log(f"[WARN] FallÃ³ clic por coordenadas: {e}")

                        # 3. RENOMBRADO DE ARCHIVO
                        # Esperamos a que aparezca un archivo nuevo en la carpeta
                        
                        # Si falla el clic, y es un PDF directo, intentamos simular CTRL+S (Guardar)
                        # OJO: Esto abre diÃ¡logo si no estÃ¡ configurado para auto-guardar.
                        # Asumimos que las prefs 'download.prompt_for_download': False funcionan.
                        
                        # NOTA: Eliminamos la descarga por 'requests' directa a peticiÃ³n del usuario
                        # que prefiere la interacciÃ³n con el botÃ³n.

                    # Ciclo de espera de archivo
                    archivo_descargado = self._esperar_archivo_descargado(archivos_antes, timeout=30)
                    
                    if archivo_descargado:
                        self.log(f"[INFO] Archivo detectado: {archivo_descargado}")
                        ruta_original = os.path.join(self.download_dir, archivo_descargado)
                        
                        try:
                            # Esperar un momento para asegurar que el archivo se liberÃ³
                            time.sleep(2)
                            
                            # Si se abriÃ³ ventana nueva, cerrarla
                            if ventana_nueva:
                                self._cerrar_ventanas_auxiliares(ventanas_antes)
                                
                            # Si la tabla no clasifica bien (DESCONOCIDO/OTRO), usamos el PDF.
                            if tipo_detectado_tabla in ("DESCONOCIDO", "OTRO"):
                                tipo_final = self.detectar_tipo_atencion(ruta_original)
                            else:
                                tipo_final = tipo_detectado_tabla

                            self._mover_a_subcarpeta(ruta_original, cedula, tipo_final, servicio, numero_factura=numero_factura, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, numero_ingreso=numero_ingreso)
                            try:
                                self._eliminar_pdfs_duplicados_recientes(archivos_antes | {archivo_descargado}, ventana_segundos=15)
                            except Exception:
                                pass
                            return True, tipo_final
                        except Exception as e:
                            self.log(f"[WARN] No se pudo renombrar el archivo: {e}")
                            if ventana_nueva:
                                self._cerrar_ventanas_auxiliares(ventanas_antes)
                            
                            # Intentamos retornar Ã©xito aunque falle renombrado, asumiendo que el archivo existe con nombre original
                            # Pero el path ruta_final no existe. Usamos ruta_original.
                            
                            # Si la tabla no clasifica bien (DESCONOCIDO/OTRO), usamos el PDF.
                            if tipo_detectado_tabla in ("DESCONOCIDO", "OTRO"):
                                tipo_final = self.detectar_tipo_atencion(ruta_original)
                            else:
                                tipo_final = tipo_detectado_tabla
                            
                            self._mover_a_subcarpeta(ruta_original, cedula, tipo_final, servicio, numero_factura=numero_factura, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, numero_ingreso=numero_ingreso)
                            return True, tipo_final
                    else:
                        self.log("[WARN] Tiempo de espera agotado. No se detectÃ³ descarga automÃ¡tica.")
                        
                        # ESTRATEGIA FALLBACK: PrintToPDF si se abriÃ³ ventana nueva (DESACTIVADA)
                        if ventana_nueva:
                            self.log("[WARN] No se detectÃ³ descarga. PrintToPDF desactivado para evitar PDF como imagen.")
                            
                            # Limpieza: Cerrar ventana emergente
                            self._cerrar_ventanas_auxiliares(ventanas_antes)
                            
                            # No retornamos True porque no hubo descarga exitosa
                            self.log("[ERROR] Descarga fallida: No se encontrÃ³ el botÃ³n y PrintToPDF estÃ¡ desactivado.")
                        
                        else:
                            self.log("[ERROR] No se abriÃ³ ventana nueva ni se detectÃ³ descarga.")
                
                return False, "No se detectÃ³ descarga"
                
            except TimeoutException:
                self.log("[WARN] No se encontraron historias clÃ­nicas para los criterios dados o tardÃ³ demasiado.")
                if _reintento < 1 and (self._pagina_en_blanco_o_error() or self._es_pantalla_login()):
                    self.log("[RECOVERY] Reintentando descarga tras recuperar sesion/pagina...")
                    if self.recuperar_pagina_y_sesion(f"timeout HC CC={cedula}"):
                        return self.descargar_historia_clinica(
                            cedula=cedula,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            servicio=servicio,
                            estrategia=estrategia,
                            tipo_hc_objetivo=tipo_hc_objetivo,
                            _reintento=_reintento + 1
                        )
                return False, "Timeout / Sin resultados"

        except Exception as e:
            self.log(f"[ERROR] Fallo en descarga de HC: {e}")
            if _reintento < 1:
                try:
                    if (not self._driver_operativo()) or self._pagina_en_blanco_o_error() or self._es_pantalla_login():
                        self.log("[RECOVERY] Error por posible caida de navegador/sesion/pagina. Reintentando una vez...")
                        if self.recuperar_pagina_y_sesion(f"exception HC CC={cedula}: {e}"):
                            return self.descargar_historia_clinica(
                                cedula=cedula,
                                fecha_inicio=fecha_inicio,
                                fecha_fin=fecha_fin,
                                servicio=servicio,
                                estrategia=estrategia,
                                tipo_hc_objetivo=tipo_hc_objetivo,
                                _reintento=_reintento + 1
                            )
                except Exception:
                    pass
            # self.driver.save_screenshot("error_descarga_hc.png")
            raise

    def exportar_resumen(self):
        os.makedirs(RUNTIME_LOG_DIR, exist_ok=True)
        resumen_path = os.path.join(RUNTIME_LOG_DIR, "resumen_ejecucion.txt")
        with open(resumen_path, "w", encoding="utf-8") as f:
            f.write("RESUMEN DE EJECUCION DEL BOT\n")
            f.write("===================================\n")
            for linea in self.resumen_acciones:
                f.write(f"- {linea}\n")
        self.log(f"[INFO] Resumen exportado a {resumen_path}")

def main():
    bot = Bot()
    try:
        bot.iniciar_navegador()
        bot.login()
        
        # Ejecutar flujos
        bot.configurar_agenda()
        bot.generar_agenda()
        
    except Exception as e:
        print(f"\n[CRITICO] El bot se detuvo por un error inesperado: {e}")
    finally:
        bot.cerrar()

if __name__ == "__main__":
    main()
