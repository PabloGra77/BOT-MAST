import hmac
import threading
import time
from functools import wraps

from flask import current_app, jsonify, request


_attempts_lock = threading.Lock()
_attempts_by_ip: dict[str, list[float]] = {}
_MAX_FAILED_ATTEMPTS = 10
_WINDOW_SECONDS = 60


def _is_rate_limited(remote_addr: str) -> bool:
    now = time.time()
    with _attempts_lock:
        attempts = _attempts_by_ip.get(remote_addr, [])
        attempts = [ts for ts in attempts if now - ts <= _WINDOW_SECONDS]
        _attempts_by_ip[remote_addr] = attempts
        return len(attempts) >= _MAX_FAILED_ATTEMPTS


def _register_failed_attempt(remote_addr: str) -> None:
    now = time.time()
    with _attempts_lock:
        attempts = _attempts_by_ip.get(remote_addr, [])
        attempts.append(now)
        _attempts_by_ip[remote_addr] = [ts for ts in attempts if now - ts <= _WINDOW_SECONDS]


def _clear_attempts(remote_addr: str) -> None:
    with _attempts_lock:
        _attempts_by_ip.pop(remote_addr, None)


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        remote_addr = request.remote_addr or "unknown"
        if _is_rate_limited(remote_addr):
            return jsonify({"error": "Too many failed authentication attempts"}), 429

        api_key = (request.headers.get("X-API-Key") or "").strip()
        expected = str(current_app.config.get("API_KEY") or "")
        if not api_key or not expected or not hmac.compare_digest(api_key, expected):
            _register_failed_attempt(remote_addr)
            return jsonify({"error": "Unauthorized"}), 401
        _clear_attempts(remote_addr)
        return fn(*args, **kwargs)

    return wrapper


def require_reset_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = str(current_app.config.get("ADMIN_RESET_TOKEN") or "").strip()
        provided = (request.headers.get("X-Reset-Token") or "").strip()
        if not expected:
            return jsonify({"error": "Reset deshabilitado: falta ADMIN_RESET_TOKEN"}), 403
        if not provided or not hmac.compare_digest(provided, expected):
            return jsonify({"error": "Unauthorized reset"}), 403
        return fn(*args, **kwargs)

    return wrapper