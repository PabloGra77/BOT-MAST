from datetime import datetime
import logging
import re
import unicodedata

import pandas as pd

logger = logging.getLogger(__name__)


def _normalizar_header(s) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[\s\-_./]+", " ", s)
    return s


def _inicio_meses_atras(fecha_str, meses_atras=1):
    try:
        fecha_norm = _normalizar_fecha_ddmmyyyy(fecha_str)
        dt = datetime.strptime(str(fecha_norm).strip(), "%d/%m/%Y")
        year = dt.year
        month = dt.month
        for _ in range(max(0, int(meses_atras))):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return f"01/{month:02d}/{year}"
    except Exception:
        return fecha_str


def _normalizar_fecha_ddmmyyyy(valor):
    if valor is None:
        return None

    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%d/%m/%Y")
        except Exception:
            pass

    s = str(valor).strip()
    if not s or s.lower() == "nan":
        return None

    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", s):
        dia, mes, anio = s.split("/")
        if len(anio) == 2:
            anio = f"20{anio}"
        try:
            dt = datetime(int(anio), int(mes), int(dia))
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return s

    formatos = (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    )
    for fmt in formatos:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    try:
        return pd.to_datetime(s, dayfirst=True).strftime("%d/%m/%Y")
    except Exception:
        return s


def extract_hc_request_data(flask_request) -> dict:
    if flask_request.content_type and "multipart/form-data" in flask_request.content_type:
        data = flask_request.form.to_dict()
        archivo = flask_request.files.get("archivo_excel")
        if archivo and archivo.filename:
            data["pacientes_excel"] = _parse_pacientes_excel(archivo)
        return data
    return flask_request.get_json(force=True)


def _parse_pacientes_excel(archivo) -> list[dict]:
    df = pd.read_excel(archivo)
    cabeceras_originales = list(df.columns)
    df.columns = [_normalizar_header(c) for c in df.columns]
    logger.info(
        "[HC EXCEL] Cabeceras detectadas: originales=%s -> normalizadas=%s",
        cabeceras_originales, list(df.columns),
    )

    def _buscar_col(opciones_exactas, contiene=None):
        norm_opts = {_normalizar_header(o) for o in opciones_exactas}
        for c in df.columns:
            if c in norm_opts:
                return c
        if contiene:
            for c in df.columns:
                for token in contiene:
                    if token in c:
                        return c
        return None

    col_cc = _buscar_col(
        ["cc", "cedula", "documento", "id", "numero documento", "no documento", "doc"],
        contiene=["cedul", "docum"],
    )
    cols_serv = [c for c in df.columns if "servic" in c or "area" in c or "especialidad" in c]
    col_est = _buscar_col(
        ["estrategia", "preferencia", "tipo", "orden"],
        contiene=["estrateg", "preferen"],
    )
    col_f_ini = _buscar_col(
        ["fecha inicio", "fecha_inicio", "desde", "f_ini", "fecha_desde",
         "fecha desde", "inicio", "fec inicio", "fecini"],
        contiene=["inici", "desde"],
    )
    col_f_fin = _buscar_col(
        ["fecha fin", "fecha_fin", "hasta", "f_fin", "fecha_hasta",
         "fecha hasta", "fin", "fec fin", "fecfin"],
        contiene=["hasta", "fin"],
    )
    col_numero_factura = _buscar_col(
        ["numero de factura", "numero_factura", "factura", "nro factura",
         "nro_factura", "no factura", "n factura"],
        contiene=["factur"],
    )
    col_numero_ingreso = _buscar_col(
        ["numero de ingreso", "numero ingreso", "numero_ingreso",
         "nro ingreso", "nro_ingreso", "no ingreso", "n ingreso", "ingreso"],
        contiene=["ingreso"],
    )

    logger.info(
        "[HC EXCEL] Columnas mapeadas: cc=%s, servicios=%s, estrategia=%s, "
        "f_inicio=%s, f_fin=%s, factura=%s, ingreso=%s",
        col_cc, cols_serv, col_est, col_f_ini, col_f_fin, col_numero_factura, col_numero_ingreso,
    )

    if not col_cc:
        raise ValueError(
            "No se encontro la columna de Cedula (CC) en el Excel. "
            f"Cabeceras detectadas: {cabeceras_originales}"
        )

    pacientes = []
    for _, row in df.iterrows():
        if pd.isna(row[col_cc]):
            continue

        cc = str(row[col_cc]).strip()
        if cc.endswith(".0"):
            cc = cc[:-2]
        if not cc or cc.lower() == "nan":
            continue

        estrategia = str(row[col_est]).strip().upper() if col_est and pd.notna(row[col_est]) else None
        fecha_inicio = _normalizar_fecha_ddmmyyyy(row[col_f_ini]) if col_f_ini and pd.notna(row[col_f_ini]) else None
        fecha_fin = _normalizar_fecha_ddmmyyyy(row[col_f_fin]) if col_f_fin and pd.notna(row[col_f_fin]) else None


        servicios = _collect_servicios(row, cols_serv)
        numero_factura = str(row[col_numero_factura]).strip() if col_numero_factura and pd.notna(row[col_numero_factura]) else None
        numero_ingreso_raw = str(row[col_numero_ingreso]).strip() if col_numero_ingreso and pd.notna(row[col_numero_ingreso]) else None
        if numero_ingreso_raw and numero_ingreso_raw.endswith(".0"):
            numero_ingreso_raw = numero_ingreso_raw[:-2]
        if numero_ingreso_raw and numero_ingreso_raw.lower() in ("nan", "none", ""):
            numero_ingreso_raw = None
        for servicio_item in servicios:
            pacientes.append(
                {
                    "cedula": cc,
                    "servicio": servicio_item,
                    "estrategia": estrategia,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "numero_factura": numero_factura,
                    "NUMERO DE FACTURA": numero_factura,
                    "numero_ingreso": numero_ingreso_raw,
                    "NUMERO DE INGRESO": numero_ingreso_raw,
                }
            )

    logger.info(
        "[HC EXCEL] Resultado: %d pacientes generados desde %d filas.",
        len(pacientes), len(df),
    )
    return pacientes


def _collect_servicios(row, cols_serv) -> list:
    if not cols_serv:
        return [None]

    servicios = []
    for col_servicio in cols_serv:
        valor_servicio = row[col_servicio]
        if pd.notna(valor_servicio):
            servicios.extend([item.strip() for item in str(valor_servicio).strip().split(",")])

    servicios = list({servicio for servicio in servicios if servicio})
    return servicios or [None]


