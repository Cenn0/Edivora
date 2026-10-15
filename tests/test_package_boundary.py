"""Regression tests for the build-only / packaged-runtime dependency boundary."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

_spec = importlib.util.spec_from_file_location(
    "edivora_package_boundary", Path(__file__).resolve().parents[1] / "tools" / "package_boundary.py")
boundary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(boundary)


class PackageBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / "app"
        self.package.mkdir()
        self.report = self.root / "report.xml"

    def write_report(self, names, *, completion="yes", unused=()):
        root = ET.Element("nuitka-compilation-report", completion=completion)
        for name in names:
            module = ET.SubElement(root, "module", name=name, kind="CompiledPythonModule")
            usages = ET.SubElement(module, "module_usages")
            for excluded in unused:
                ET.SubElement(usages, "module_usage", name=excluded, finding="not-found")
        ET.ElementTree(root).write(self.report, encoding="utf-8")

    def test_exact_exclusions_do_not_disable_onnxruntime(self):
        self.assertEqual(boundary.runtime_exclusion_arguments(),
                         ["--nofollow-import-to=torch", "--nofollow-import-to=onnx"])

    def test_runtime_and_onnx_model_files_remain_allowed(self):
        self.write_report(["local_ai_photo_editor", "onnxruntime", "onnxruntime.capi._pybind_state", "numpy"])
        models = self.package / "local_ai_photo_editor" / "models"
        models.mkdir(parents=True)
        (models / "dncnn_color_blind.onnx").write_bytes(b"test model placeholder")
        boundary.verify_runtime_boundary(self.report, self.package)

    def test_included_converter_roots_and_submodules_are_rejected(self):
        for name in ("torch", "torch.nn.functional", "onnx", "onnx.helper"):
            with self.subTest(name=name):
                self.write_report(["onnxruntime", name])
                with self.assertRaisesRegex(RuntimeError, "Build-only libraries"):
                    boundary.verify_runtime_boundary(self.report, self.package)

    def test_intentionally_excluded_import_usages_are_not_included_modules(self):
        self.write_report(["onnxruntime"], unused=("torch", "onnx"))
        boundary.verify_runtime_boundary(self.report, self.package)

    def test_incomplete_or_empty_reports_fail_closed(self):
        for names, completion in ((["onnxruntime"], "no"), ([], "yes")):
            with self.subTest(names=names, completion=completion):
                self.write_report(names, completion=completion)
                with self.assertRaises(RuntimeError):
                    boundary.verify_runtime_boundary(self.report, self.package)

    def test_converter_data_directories_are_rejected_case_insensitively(self):
        self.write_report(["onnxruntime"])
        unwanted = self.package / "Torch"
        unwanted.mkdir()
        with self.assertRaisesRegex(RuntimeError, "Build-only package directory"):
            boundary.verify_runtime_boundary(self.report, self.package)
