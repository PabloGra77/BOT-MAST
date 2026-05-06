import logging

from flask import Blueprint, jsonify, request

from ..application.hc_excel import extract_hc_request_data
from ..application.job_service import (
    clear_all_jobs,
    continuar_job_hc,
    crear_job_agenda,
    crear_job_hc,
    detener_job,
    get_job_snapshot,
)
from ..domain.requests import AgendaRequest, HCRequest
from .security import require_api_key, require_reset_token


api_bp = Blueprint("agenda_api", __name__)
logger = logging.getLogger(__name__)


def _job_public_view(job: dict) -> dict:
    # Evita exponer objetos no serializables (Event, request dataclass, etc.)
    # que rompen jsonify y terminan devolviendo HTML de error.
    if not isinstance(job, dict):
        return {"status": "error", "detail": "Estado de job inválido"}
    bloqueados = {"stop_event", "request"}
    return {k: v for k, v in job.items() if k not in bloqueados}


@api_bp.route("/agenda", methods=["POST"])
@require_api_key
def crear_agenda():
    try:
        data = request.get_json(force=True)
        req = AgendaRequest.from_dict(data)
        job_id = crear_job_agenda(req)
        return jsonify({"job_id": job_id}), 202
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.route("/hc", methods=["POST"])
@require_api_key
def descargar_hc():
    try:
        data = extract_hc_request_data(request)
        req = HCRequest.from_dict(data)
        job_id = crear_job_hc(req)
        return jsonify({"job_id": job_id}), 202
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Error interno creando job de HC")
        return jsonify({"error": "Error interno del servidor"}), 500


@api_bp.route("/agenda/<job_id>", methods=["GET"])
@require_api_key
def estado_agenda(job_id):
    job = get_job_snapshot(job_id)
    if not job:
        return jsonify({"error": "Job no encontrado"}), 404
    return jsonify(_job_public_view(job))


@api_bp.route("/agenda/<job_id>/stop", methods=["POST"])
@require_api_key
def detener_job_api(job_id):
    ok, msg = detener_job(job_id)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "message": msg}), 200


@api_bp.route("/agenda/<job_id>/continue", methods=["POST"])
@require_api_key
def continuar_job_api(job_id):
    ok, msg, new_job_id = continuar_job_hc(job_id)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "message": msg, "job_id": new_job_id}), 200


@api_bp.route("/ping", methods=["GET"])
@require_api_key
def ping():
    return jsonify({"ok": True}), 200


@api_bp.route("/reset", methods=["POST"])
@require_api_key
@require_reset_token
def reset_server():
    try:
        cleared = clear_all_jobs()

        import subprocess

        try:
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], capture_output=True)
        except Exception:
            logger.exception("No fue posible limpiar procesos de navegador durante reset")

        return jsonify({"ok": True, "message": "Servidor reseteado y procesos limpiados", "jobs_cleared": cleared}), 200
    except Exception:
        logger.exception("Error interno durante reset")
        return jsonify({"error": "Error interno del servidor"}), 500