"""Локальный демонстрационный JSON-интерфейс baseline ЛР7."""

import hashlib
import json
import re
import sys
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().with_name("model.json")
MODEL_SHA256 = "2caf0de861ba2c41694d3b352c52c58fa1f6c5885fdc604c1257655e76eace3e"
EXPECTED_MODEL = {
    "model_id": "baseline-lr07-kaizen-v1",
    "target": "implemented_90d",
    "estimator": "train majority",
    "tie_breaker": 0,
    "prediction": 0,
}
LIMITATIONS = ["demo_only", "constant_prediction", "not_for_automatic_decisions"]
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}", re.ASCII)


def error(code, request_id=None):
    message = ("Некорректный вход." if code == "invalid_input"
               else "Модель недоступна; рассмотрите заявку вручную.")
    return {"schema_version": "1.0", "request_id": request_id, "status": "error",
            "error": {"code": code, "message": message}}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def load_model(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MODEL_SHA256:
        raise ValueError("artifact checksum mismatch")
    model = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if model != EXPECTED_MODEL:
        raise ValueError("incompatible model")
    return model


def handle(raw, model_path=None):
    """Принять UTF-8 JSON (bytes или str), вернуть один словарь ответа."""
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        request = json.loads(raw, object_pairs_hook=unique_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeDecodeError, TypeError, RecursionError):
        return error("invalid_input")

    request_id = request.get("request_id") if isinstance(request, dict) else None
    valid_id = isinstance(request_id, str) and ID_PATTERN.fullmatch(request_id) is not None
    safe_id = request_id if valid_id else None
    if (not isinstance(request, dict) or set(request) != {"schema_version", "request_id"}
            or request.get("schema_version") != "1.0" or not valid_id):
        return error("invalid_input", safe_id)
    try:
        model = load_model(MODEL_PATH if model_path is None else model_path)
        return {"schema_version": "1.0", "request_id": request_id, "status": "ok",
                "model_id": model["model_id"],
                "prediction": {"target": model["target"], "class": model["prediction"]},
                "limitations": LIMITATIONS.copy()}
    except Exception:
        return error("model_unavailable", request_id)


def main():
    result = handle(sys.stdin.buffer.read())
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return {"ok": 0, "invalid_input": 2, "model_unavailable": 3}[
        "ok" if result["status"] == "ok" else result["error"]["code"]]


if __name__ == "__main__":
    sys.exit(main())
