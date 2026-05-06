from datetime import datetime
import re

import pandas as pd




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
    df.columns = [str(c).lower().strip() for c in df.columns]

    col_cc = next((c for c in df.columns if c in ["cc", "cedula", "documento", "id"]), None)
    cols_serv = [c for c in df.columns if "servicio" in c or "area" in c]
    if not cols_serv:
        cols_serv = [c for c in df.columns if c in ["servicio", "area"]]

    col_est = next((c for c in df.columns if c in ["estrategia", "preferencia", "tipo"]), None)
    col_f_ini = next((c for c in df.columns if c in ["fecha inicio", "fecha_inicio", "desde", "f_ini", "fecha_desde"]), None)
    col_f_fin = next((c for c in df.columns if c in ["fecha fin", "fecha_fin", "hasta", "f_fin", "fecha_hasta"]), None)
    col_numero_factura = next((c for c in df.columns if c in ["numero de factura", "numero_factura", "factura", "nro factura", "nro_factura"]), None)

    if not col_cc:
        raise ValueError("No se encontró la columna de Cédula (CC) en el Excel")

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
                }
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


