from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "experiments" / "validate-experiments.py"

spec = importlib.util.spec_from_file_location("validate_experiments", VALIDATOR_PATH)
assert spec is not None and spec.loader is not None
validator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator_module)

validate_records = validator_module.validate_records


def load_inputs() -> tuple[dict, dict, dict, dict, dict, dict]:
    protocol_registry = json.loads(
        (ROOT / "data" / "experiments" / "protocols.json").read_text(encoding="utf-8")
    )
    result_registry = json.loads(
        (ROOT / "data" / "experiments" / "results.json").read_text(encoding="utf-8")
    )
    protocol_schema = json.loads(
        (ROOT / "schemas" / "experiment-protocol.schema.json").read_text(encoding="utf-8")
    )
    result_schema = json.loads(
        (ROOT / "schemas" / "experiment-result.schema.json").read_text(encoding="utf-8")
    )
    matrix = json.loads(
        (ROOT / "data" / "builds" / "version-matrix.json").read_text(encoding="utf-8")
    )
    artifacts = yaml.safe_load(
        (ROOT / "data" / "artifacts" / "diagnostic-manifest.yaml").read_text(
            encoding="utf-8"
        )
    )
    return protocol_registry, result_registry, protocol_schema, result_schema, matrix, artifacts


class ExperimentRecordValidationTest(unittest.TestCase):
    def test_repository_protocols_and_results_validate(self) -> None:
        errors = validate_records(*load_inputs())
        self.assertEqual([], errors)

    def test_cli_validates_repository_registries(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("Experiment validation passed", result.stdout)

    def test_prohibited_negative_generalization_is_rejected(self) -> None:
        inputs = list(load_inputs())
        result_registry = copy.deepcopy(inputs[1])
        result_registry["results"][0]["outcome"]["negativeResultStatement"] = (
            "The feature is impossible because the widget route did not switch."
        )
        inputs[1] = result_registry

        errors = validate_records(*inputs)

        self.assertTrue(
            any("negativeResultStatement" in error for error in errors),
            errors,
        )
        self.assertTrue(any("prohibited generalization" in error for error in errors), errors)

    def test_artifact_hash_drift_is_rejected(self) -> None:
        inputs = list(load_inputs())
        result_registry = copy.deepcopy(inputs[1])
        result_registry["results"][0]["artifacts"][0]["sha256"] = "0" * 64
        inputs[1] = result_registry

        errors = validate_records(*inputs)

        self.assertTrue(any("does not match diagnostic manifest" in error for error in errors), errors)

    def test_missing_control_result_is_rejected(self) -> None:
        inputs = list(load_inputs())
        result_registry = copy.deepcopy(inputs[1])
        result_registry["results"][0]["controls"]["positive"].pop()
        inputs[1] = result_registry

        errors = validate_records(*inputs)

        self.assertTrue(any("positive control IDs" in error for error in errors), errors)

    def test_completed_result_requires_exact_timing_and_tool_version(self) -> None:
        inputs = list(load_inputs())
        result_registry = copy.deepcopy(inputs[1])
        record = result_registry["results"][0]
        record["status"] = "completed"
        inputs[1] = result_registry

        errors = validate_records(*inputs)

        self.assertTrue(any("precision" in error for error in errors), errors)
        self.assertTrue(any("version" in error for error in errors), errors)
        self.assertTrue(any("startedAt" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
