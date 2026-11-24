"""Фактические синтетические ответы в отдельных процессах и при отказе модели."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import baseline

HERE = Path(__file__).resolve().parent
cases = [
    ("обычный", {"schema_version": "1.0", "request_id": "demo-001"}, 0),
    ("граница 64", {"schema_version": "1.0", "request_id": "a" * 64}, 0),
    ("слишком длинный", {"schema_version": "1.0", "request_id": "a" * 65}, 2),
    ("пустой объект", {}, 2),
    ("неверный тип", {"schema_version": "1.0", "request_id": 42}, 2),
    ("лишнее поле", {"schema_version": "1.0", "request_id": "demo", "extra": 1}, 2),
]
for name, request, expected in cases:
    run = subprocess.run([sys.executable, "-B", str(HERE / "baseline.py")],
                         input=json.dumps(request).encode(), capture_output=True, check=False)
    if run.returncode != expected or run.stderr:
        raise RuntimeError(f"Неожиданный результат: {name}")
    print(json.dumps({"case": name, "input": request, "exit_code": run.returncode,
                      "output": json.loads(run.stdout)}, ensure_ascii=False))
with tempfile.TemporaryDirectory() as tmp:
    request = {"schema_version": "1.0", "request_id": "demo-001"}
    result = baseline.handle(json.dumps(request), Path(tmp) / "missing.json")
    if result.get("error", {}).get("code") != "model_unavailable":
        raise RuntimeError("Отказ модели не обнаружен")
    print(json.dumps({"case": "нет модели (вызов функции)", "input": request,
                      "output": result}, ensure_ascii=False))
