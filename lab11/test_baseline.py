import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import baseline

HERE = Path(__file__).resolve().parent


class BaselineTests(unittest.TestCase):
    def test_normal_and_boundary(self):
        for ident in ("demo-001", "a" * 64):
            with self.subTest(ident=ident):
                response = baseline.handle(json.dumps({"schema_version": "1.0", "request_id": ident}))
                self.assertEqual(response["status"], "ok")
                self.assertEqual(response["request_id"], ident)
                self.assertEqual(response["prediction"], {"target": "implemented_90d", "class": 0})
                self.assertEqual(response["limitations"], ["demo_only", "constant_prediction", "not_for_automatic_decisions"])

    def test_invalid_never_loads_model(self):
        inputs = [
            b"", b"not json", b"\xff", b"{}", b"[]", b"null",
            b'{"schema_version":"1.0","request_id":"a","request_id":"b"}',
            json.dumps({"schema_version": "2.0", "request_id": "valid"}),
            json.dumps({"schema_version": "1.0", "request_id": "a" * 65}),
            json.dumps({"schema_version": "1.0", "request_id": "ё"}),
            json.dumps({"schema_version": "1.0", "request_id": "bad id"}),
            json.dumps({"schema_version": "1.0", "request_id": 123}),
            json.dumps({"schema_version": "1.0", "request_id": "valid", "extra": 1}),
        ]
        with patch.object(baseline, "load_model", side_effect=AssertionError("called")):
            for raw in inputs:
                with self.subTest(raw=raw):
                    result = baseline.handle(raw)
                    self.assertEqual(result["error"]["code"], "invalid_input")
                    self.assertNotIn("prediction", result)
                    self.assertNotIn("model_id", result)

    def test_model_unavailable_and_tampering(self):
        request = b'{"schema_version":"1.0","request_id":"test"}'
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "model.json"
            for value in (None, b'{"prediction":1}', (HERE / "model.json").read_bytes() + b" "):
                if value is not None:
                    artifact.write_bytes(value)
                result = baseline.handle(request, artifact)
                self.assertEqual(result, baseline.error("model_unavailable", "test"))
                self.assertNotIn("prediction", result)

    def test_included_hashes(self):
        manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
        for name in ("baseline.py", "model.json"):
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), manifest["files"][name])
        self.assertEqual(manifest["files"]["model.json"], baseline.MODEL_SHA256)

    def test_cli_exit_and_stdout(self):
        for data, code in [(b'{"schema_version":"1.0","request_id":"demo-001"}', 0), (b"{}", 2)]:
            run = subprocess.run([sys.executable, "-B", str(HERE / "baseline.py")], input=data, capture_output=True)
            self.assertEqual(run.returncode, code)
            self.assertEqual(run.stderr, b"")
            self.assertIsInstance(json.loads(run.stdout), dict)


if __name__ == "__main__":
    unittest.main()
