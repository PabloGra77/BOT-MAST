import logging
import uuid
import ctypes
import threading
from copy import deepcopy
from datetime import datetime, timezone
from threading import Event, Thread
from typing import Dict

from ..bot.runner import run_bot_job, run_hc_job
from ..domain.requests import AgendaRequest, HCRequest


logger = logging.getLogger(__name__)
jobs: Dict[str, dict] = {}
_jobs_lock = threading.RLock()


def _set_job_fields(job_id: str, **fields) -> bool:
    with _jobs_lock:
        job = jobs.get(job_id)
        if not isinstance(job, dict):
            return False
        job.update(fields)
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        return True


def _get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        job = jobs.get(job_id)
        return job if isinstance(job, dict) else None


def get_job_snapshot(job_id: str) -> dict | None:
    with _jobs_lock:
        job = jobs.get(job_id)
        if not isinstance(job, dict):
            return None
        return dict(job)


def clear_all_jobs() -> int:
    with _jobs_lock:
        total = len(jobs)
        jobs.clear()
        return total


class _WindowsKeepAwake:
    """
    Mantiene activo el equipo durante la ejecución del job para evitar
    suspensión por inactividad (cuando la política del equipo lo permita).
    """

    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002

    def __init__(self):
        self._enabled = False
        self._stop_event = threading.Event()
        self._thread = None

    def _tick(self):
        while not self._stop_event.is_set():
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED | self.ES_DISPLAY_REQUIRED
                )
            except Exception:
                break
            self._stop_event.wait(50)

    def start(self):
        if self._enabled:
            return
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED | self.ES_DISPLAY_REQUIRED
            )
            self._enabled = True
            self._thread = threading.Thread(target=self._tick, daemon=True)
            self._thread.start()
            logger.info("Keep-awake activo durante ejecución del job")
        except Exception as exc:
            logger.warning("No fue posible activar keep-awake: %s", exc)

    def stop(self):
        if not self._enabled:
            return
        self._stop_event.set()
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
        except Exception:
            pass
        self._enabled = False
        logger.info("Keep-awake desactivado")


def crear_job_agenda(req: AgendaRequest) -> str:
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        jobs[job_id] = {
            "status": "pending",
            "detail": "Job creado",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "type": "agenda",
            "stop_event": Event(),
        }
    thread = Thread(target=_ejecutar_job_agenda, args=(job_id, req), daemon=True)
    thread.start()
    return job_id


def crear_job_hc(req: HCRequest) -> str:
    job_id = str(uuid.uuid4())
    req_copy = deepcopy(req)
    with _jobs_lock:
        jobs[job_id] = {
            "status": "pending",
            "detail": "Job HC en cola",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "type": "hc",
            "progress_total": 0,
            "progress_completed": 0,
            "progress_percent": 0,
            "current_item": "",
            "stop_event": Event(),
            "request": req_copy,
        }
    thread = Thread(target=_ejecutar_job_hc, args=(job_id, deepcopy(req_copy)), daemon=True)
    thread.start()
    return job_id


def _ejecutar_job_agenda(job_id: str, req: AgendaRequest) -> None:
    keep_awake = _WindowsKeepAwake()
    try:
        job = _get_job(job_id)
        if not job:
            return
        stop_event = job.get("stop_event")
        if stop_event and stop_event.is_set():
            _set_job_fields(job_id, status="stopped", detail="Job detenido antes de iniciar")
            return
        _set_job_fields(job_id, status="running", detail="Iniciando Bot de Agenda...")
        keep_awake.start()
        run_bot_job(req)
        if stop_event and stop_event.is_set():
            _set_job_fields(job_id, status="stopped", detail="Job detenido por usuario")
            return
        _set_job_fields(job_id, status="finished", detail="Agenda generada correctamente")
    except Exception as exc:
        logger.exception("Error ejecutando job %s", job_id)
        _set_job_fields(job_id, status="error", detail=str(exc))
    finally:
        keep_awake.stop()


def _ejecutar_job_hc(job_id: str, req: HCRequest) -> None:
    keep_awake = _WindowsKeepAwake()
    try:
        job = _get_job(job_id)
        if not job:
            return
        stop_event = job.get("stop_event")
        if stop_event and stop_event.is_set():
            _set_job_fields(job_id, status="stopped", detail="Job HC detenido antes de iniciar")
            return
        _set_job_fields(job_id, status="running", detail="Iniciando Bot de Historias Clínicas...")
        keep_awake.start()
        def progress_callback(payload: dict):
            if not isinstance(payload, dict):
                return
            total = int(payload.get("total") or 0)
            completed = int(payload.get("completed") or 0)
            percent = int((completed / total) * 100) if total > 0 else 0
            _set_job_fields(
                job_id,
                progress_total=total,
                progress_completed=completed,
                progress_percent=percent,
                current_item=str(payload.get("current_item") or ""),
                detail=str(payload.get("detail") or "Procesando..."),
                status=str(payload.get("status") or "running"),
            )

        resultado = run_hc_job(req, stop_event=stop_event, progress_callback=progress_callback)
        if resultado.get("detenido") or (stop_event and stop_event.is_set()):
            _set_job_fields(
                job_id,
                status="stopped",
                progress_completed=resultado.get("con_hc", 0) + resultado.get("sin_hc", 0) + resultado.get("fallos", 0),
                detail=(
                "Detenido por usuario. "
                f"Con HC: {resultado.get('con_hc', 0)}, "
                f"Sin HC: {resultado.get('sin_hc', 0)}, "
                f"Fallos: {resultado.get('fallos', 0)}. "
                f"Informe: {resultado.get('ruta_informe', 'N/A')}"
                ),
            )
        else:
            _set_job_fields(
                job_id,
                status="finished",
                progress_completed=resultado.get("con_hc", 0) + resultado.get("sin_hc", 0) + resultado.get("fallos", 0),
                progress_percent=100,
                detail=(
                "Historia Clínica descargada correctamente. "
                f"Informe: {resultado.get('ruta_informe', 'N/A')}"
                ),
            )
    except Exception as exc:
        logger.exception("Error ejecutando job HC %s", job_id)
        _set_job_fields(job_id, status="error", detail=str(exc))
    finally:
        keep_awake.stop()


def detener_job(job_id: str) -> tuple[bool, str]:
    with _jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return False, "Job no encontrado"

        if job.get("status") in ("finished", "error", "stopped"):
            return False, f"No se puede detener: job en estado {job.get('status')}"

        stop_event = job.get("stop_event")
        if stop_event:
            stop_event.set()
        job["status"] = "stopping"
        job["detail"] = "Solicitud de detención enviada. Esperando cierre seguro e informe parcial..."
        return True, "Detención solicitada"


def continuar_job_hc(job_id: str) -> tuple[bool, str, str | None]:
    with _jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return False, "Job no encontrado", None

        if job.get("type") != "hc":
            return False, "Solo se puede continuar un job de HC", None

        if job.get("status") not in ("stopped", "error"):
            return False, f"El job está en estado {job.get('status')}, no se puede continuar", None

        req = job.get("request")
        if req is None:
            return False, "No se encontró el request original para continuar", None

        if job.get("resumed_to"):
            return False, "Este job ya fue continuado", None

        new_job_id = crear_job_hc(deepcopy(req))
        job["resumed_to"] = new_job_id
        jobs[new_job_id]["resumed_from"] = job_id

    return True, "Continuación iniciada", new_job_id