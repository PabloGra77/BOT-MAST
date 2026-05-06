import os
import re
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import glob
_candidatos = glob.glob(os.path.join(BASE_DIR, "usuario", "USUARIOS*.xlsx"))
EXCEL_PATH = _candidatos[0] if _candidatos else os.path.join(BASE_DIR, "usuario", "USUARIOS.xlsx")


def norm(v):
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


def main():
    try:
        df = pd.read_excel(EXCEL_PATH)
    except PermissionError:
        import shutil
        temp_path = os.path.join(BASE_DIR, "temp_users_read.xlsx")
        shutil.copy2(EXCEL_PATH, temp_path)
        df = pd.read_excel(temp_path)
    print("COLUMNAS:", list(df.columns))
    objetivo = "29816379"
    objetivo_norm = norm(objetivo)
    print("cc_norm:", objetivo_norm)
    encontrado = False
    for col in df.columns:
        vals = df[col].map(norm)
        if (vals == objetivo_norm).any():
            print("MATCH_EN_COLUMNA:", col)
            print(df.loc[vals == objetivo_norm].head())
            encontrado = True
    if not encontrado:
        print("NO_SE_ENCONTRO")


if __name__ == "__main__":
    main()
