from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgendaRequest:
    sede: str
    cc: str
    fecha: str
    hora_inicio: str
    duracion_min: int
    cantidad: int

    @classmethod
    def from_dict(cls, data):
        sede = str(data.get("sede", "")).strip()
        cc = str(data.get("cc", "")).strip()
        fecha = str(data.get("fecha", "")).strip()
        hora_inicio = str(data.get("hora_inicio", "")).strip()
        duracion_min = int(data.get("duracion_min", 0))
        cantidad = int(data.get("cantidad", 0))
        errors = []
        if not sede:
            errors.append("La sede es obligatoria")
        if not cc.isdigit():
            errors.append("La cédula debe ser numérica")
        if fecha.lower() != "hoy":
            try:
                datetime.strptime(fecha, "%d/%m/%Y")
            except ValueError:
                errors.append("Fecha inválida, use DD/MM/YYYY o 'hoy'")
        try:
            datetime.strptime(hora_inicio, "%H:%M")
        except ValueError:
            errors.append("Hora inválida, use HH:MM")
        if duracion_min <= 0:
            errors.append("La duración debe ser mayor que 0")
        if cantidad <= 0:
            errors.append("La cantidad debe ser mayor que 0")
        if errors:
            raise ValueError("; ".join(errors))
        return cls(
            sede=sede,
            cc=cc,
            fecha=fecha,
            hora_inicio=hora_inicio,
            duracion_min=duracion_min,
            cantidad=cantidad,
        )


@dataclass
class HCRequest:
    cedula: str
    fecha_inicio: str
    fecha_fin: str
    servicio: str = "Todos"
    estrategia: str = "RECIENTE"
    ruta_descarga: str = ""
    pacientes_excel: list = None

    @classmethod
    def from_dict(cls, data):
        cedula = str(data.get("cedula", "")).strip()
        fecha_inicio = str(data.get("fecha_inicio", "")).strip()
        fecha_fin = str(data.get("fecha_fin", "")).strip()
        servicio = str(data.get("servicio", "Todos")).strip()
        estrategia = str(data.get("estrategia", "RECIENTE")).strip().upper()
        ruta_descarga = str(data.get("ruta_descarga", "")).strip()
        pacientes_excel = data.get("pacientes_excel", None)

        errors = []
        if not cedula and not pacientes_excel:
            errors.append("Debe ingresar cédulas manualmente o cargar un archivo Excel.")

        if pacientes_excel is not None:
            if not isinstance(pacientes_excel, list):
                errors.append("pacientes_excel debe ser una lista")
            else:
                for idx, item in enumerate(pacientes_excel):
                    if not isinstance(item, dict):
                        errors.append(f"pacientes_excel[{idx}] debe ser un objeto")
                        continue
                    ced = str(item.get("cedula", "")).strip()
                    if not ced:
                        errors.append(f"pacientes_excel[{idx}] debe incluir 'cedula'")

        if cedula:
            cedulas_temp = [item.strip() for item in cedula.replace(",", "\n").split("\n") if item.strip()]
            if not cedulas_temp:
                errors.append("Debe ingresar al menos una cédula válida.")

        if fecha_inicio:
            if fecha_inicio.lower() == "hoy":
                fecha_inicio = datetime.now().strftime("%d/%m/%Y")
            else:
                try:
                    datetime.strptime(fecha_inicio, "%d/%m/%Y")
                except ValueError:
                    errors.append("Fecha inicio inválida, use DD/MM/YYYY o 'hoy'")

        if fecha_fin:
            if fecha_fin.lower() == "hoy":
                fecha_fin = datetime.now().strftime("%d/%m/%Y")
            else:
                try:
                    datetime.strptime(fecha_fin, "%d/%m/%Y")
                except ValueError:
                    errors.append("Fecha fin inválida, use DD/MM/YYYY o 'hoy'")

        if errors:
            raise ValueError("; ".join(errors))

        return cls(
            cedula=cedula,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            servicio=servicio,
            estrategia=estrategia,
            ruta_descarga=ruta_descarga,
            pacientes_excel=pacientes_excel,
        )