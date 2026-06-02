from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from .settings import JOB_CONFIG_DIR, load_main_config


def _set_profesional(config: dict, sede: str, nombre_config: str) -> None:
    config.setdefault("profesional", {})
    config["profesional"]["sede"] = sede

    parts = str(nombre_config or "").strip().upper().split()
    if len(parts) == 4:
        config["profesional"]["primer_nombre"] = parts[0]
        config["profesional"]["segundo_nombre"] = "" if parts[1] == "X" else parts[1]
        config["profesional"]["primer_apellido"] = parts[2]
        config["profesional"]["segundo_apellido"] = "" if parts[3] == "X" else parts[3]
    elif len(parts) >= 2:
        config["profesional"]["primer_nombre"] = parts[0]
        config["profesional"]["primer_apellido"] = parts[-1]


def _set_agenda(config: dict, fecha_str: str, hora_inicio: str, duracion_min: int, cantidad: int) -> None:
    inicio_dt = datetime.strptime(f"{fecha_str} {hora_inicio}", "%d/%m/%Y %H:%M")
    fin_dt = inicio_dt + timedelta(minutes=duracion_min * cantidad)

    mapa_dias = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }
    dia_semana = inicio_dt.strftime("%A")

    config.setdefault("configuracion_agenda", {})
    config["configuracion_agenda"]["dias_atencion"] = [mapa_dias.get(dia_semana, dia_semana)]
    config["configuracion_agenda"]["horarios"] = [
        {
            "inicio": hora_inicio,
            "fin": fin_dt.strftime("%H:%M"),
            "duracion": duracion_min,
        }
    ]

    config.setdefault("generacion_agenda", {})
    config["generacion_agenda"]["fecha_inicio"] = fecha_str
    config["generacion_agenda"]["fecha_fin"] = fecha_str


def build_agenda_runtime_config(
    *,
    sede: str,
    nombre_profesional: str,
    fecha_str: str,
    hora_inicio: str,
    duracion_min: int,
    cantidad: int,
    source: str,
) -> str:
    config = deepcopy(load_main_config())
    _set_profesional(config, sede, nombre_profesional)
    _set_agenda(config, fecha_str, hora_inicio, duracion_min, cantidad)

    JOB_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    runtime_path = JOB_CONFIG_DIR / f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.json"
    with runtime_path.open("w", encoding="utf-8") as runtime_file:
        json.dump(config, runtime_file, indent=4, ensure_ascii=False)
    return str(runtime_path)


def cleanup_runtime_config(config_path: str | Path | None) -> None:
    if not config_path:
        return
    path = Path(config_path)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass