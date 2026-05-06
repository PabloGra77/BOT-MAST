import os
import re
import pandas as pd
import numpy as np
from ..config import Config


def _norm(v):
    if pd.isna(v):
        return ""
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return str(int(v))
    s = str(v).strip()
    s = re.sub(r"[^0-9]", "", s)
    s = s.lstrip("0")
    return s


def buscar_profesional_por_cc(cc_input):
    original_path = Config.USERS_EXCEL_PATH
    try:
        df = pd.read_excel(original_path)
    except PermissionError:
        import shutil
        temp_path = os.path.join(Config.BASE_DIR, "temp_users_read.xlsx")
        shutil.copy2(original_path, temp_path)
        df = pd.read_excel(temp_path)
    cols = [c.strip() for c in df.columns.tolist()]
    df.columns = cols
    cc_norm = _norm(cc_input)
    target_col = None
    prefer = [
        "NUMERO IDE",
        "NUMERO_IDE",
        "NUMERO IDENTIFICACION",
        "NUMERO IDENTIFICACIÓN",
        "NUMERO IDENT",
        "NUMERO DOCUMENTO",
        "DOCUMENTO",
        "CC",
        "CEDULA",
        "CÉDULA",
    ]
    for name in prefer:
        if name in df.columns:
            target_col = name
            break
    if target_col is None:
        for c in df.columns:
            u = c.upper()
            if "NUMERO" in u and ("IDE" in u or "IDENT" in u or "DOC" in u or "CED" in u or "ID" in u):
                target_col = c
                break
    row = None
    if target_col is not None:
        col_vals = df[target_col].map(_norm)
        idx = col_vals[col_vals == cc_norm].index
        if len(idx) > 0:
            row = df.loc[idx[0]]
    if row is None:
        for c in df.columns:
            vals = df[c].map(_norm)
            idx = vals[vals == cc_norm].index
            if len(idx) > 0:
                row = df.loc[idx[0]]
                break
    if row is None:
        return None
    p_nom = str(row.get("PRI. NOMBRE", "")).strip()
    s_nom_val = row.get("SEG. NOMBRE", None)
    s_nom = str(s_nom_val).strip() if pd.notna(s_nom_val) else "X"
    p_ape = str(row.get("PRI. APELLIDO", "")).strip()
    s_ape_val = row.get("SEG. APELLIDO", None)
    s_ape = str(s_ape_val).strip() if pd.notna(s_ape_val) else "X"
    nombre_mostrar = f"{p_nom} {s_nom if s_nom != 'X' else ''} {p_ape} {s_ape if s_ape != 'X' else ''}".replace("  ", " ").strip()
    nombre_config = f"{p_nom} {s_nom} {p_ape} {s_ape}"
    return {
        "nombre_mostrar": nombre_mostrar,
        "nombre_config": nombre_config,
        "login": row.get("LOGIN", ""),
        "especialidad": row.get("ESPECIALIDAD", ""),
    }

