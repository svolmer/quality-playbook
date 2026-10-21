"""Compat fork v1.6.0-maf.3, CC-22: ``qpb_validate --host-mode maf``.

A host that owns every AI call (the QualityPlaybook.Agent MCP host) runs
no AI CLI, so Phase 0's ``ai_cli_not_on_path`` finding is a false
blocker there. ``--host-mode maf`` is the explicit declaration that
skips that one check. These tests pin three things:

* the skip is real and visible (an ``event=info`` line says so);
* it is the ONLY thing skipped: the closure, scaffolding, Python and
  bash checks all still run and still fail;
* it is never inferred: without the flag the finding is unchanged, and
  an unknown mode is refused.
"""

from __future__ import annotations

import collections
import io
import shutil
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from bin import qpb_validate as v

_QPB_ROOT = Path(__file__).resolve().parents[2]
_INSTALLER = _QPB_ROOT / "bin" / "install_skill.py"

_NO_AI_CLI = "definitely-not-an-installed-ai-cli"


def _run_main(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = v.main(argv)
    return rc, buf.getvalue()


def _install(target: Path) -> None:
    subprocess.run(
        [sys.executable, str(_INSTALLER), "--into", str(target),
         "--ai-tool", "claude"],
        check=True, capture_output=True)


def _without_claude_on_path(real_which=shutil.which):
    """A `shutil.which` that cannot find the `claude` CLI but finds the rest."""
    return lambda name, *a, **k: None if name == "claude" else real_which(name, *a, **k)


class CheckEnvironmentHostModeTests(unittest.TestCase):

    def test_without_host_mode_a_missing_ai_cli_is_a_finding(self) -> None:
        findings, _ = v.check_environment(_NO_AI_CLI)
        self.assertEqual(
            [f["code"] for f in findings], ["ai_cli_not_on_path"])

    def test_host_mode_maf_skips_the_check_and_says_so(self) -> None:
        findings, infos = v.check_environment(_NO_AI_CLI, host_mode="maf")
        self.assertNotIn("ai_cli_not_on_path", [f["code"] for f in findings])
        skipped = [i for i in infos if i.get("ai_cli_check") == "skipped"]
        self.assertEqual(len(skipped), 1, infos)
        self.assertEqual(skipped[0]["host_mode"], "maf")
        self.assertEqual(skipped[0]["tool"], _NO_AI_CLI)
        self.assertEqual(skipped[0]["event"], "info")

    def test_host_mode_does_not_skip_the_python_version_check(self) -> None:
        old = collections.namedtuple(
            "V", "major minor micro releaselevel serial")(3, 9, 0, "final", 0)
        with mock.patch.object(v.sys, "version_info", old):
            findings, _ = v.check_environment(_NO_AI_CLI, host_mode="maf")
        self.assertIn("python_version_too_old", [f["code"] for f in findings])

    def test_host_mode_does_not_skip_the_bash_info(self) -> None:
        real = shutil.which
        with mock.patch.object(
                v.shutil, "which",
                lambda name, *a, **k: None if name == "bash" else real(name, *a, **k)):
            _, infos = v.check_environment(_NO_AI_CLI, host_mode="maf")
        self.assertTrue(any(i.get("bash") == "unavailable" for i in infos), infos)

    def test_host_mode_with_no_cli_tool_adds_nothing(self) -> None:
        """No detected AI tool means there was no CLI check to skip."""
        _, infos = v.check_environment(None, host_mode="maf")
        self.assertFalse(any("ai_cli_check" in i for i in infos), infos)


class ValidatorHostModeEndToEndTests(unittest.TestCase):

    def test_host_mode_turns_a_clean_install_ok_when_the_cli_is_absent(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td).resolve()
            _install(target)
            (target / "reference_docs" / "cite").mkdir(parents=True)
            (target / "quality").mkdir(exist_ok=True)
            (target / "quality" / "RUN_INDEX.md").write_text("# Run Index\n", encoding="utf-8")
            (target / ".gitignore").write_text("quality/\n", encoding="utf-8")
            with mock.patch.object(v.shutil, "which", _without_claude_on_path()):
                rc_without, out_without = _run_main([str(target)])
                rc_with, out_with = _run_main([str(target), "--host-mode", "maf"])
        self.assertNotEqual(rc_without, 0, out_without)
        self.assertIn("finding=ai_cli_not_on_path", out_without)
        self.assertEqual(rc_with, 0, out_with)
        self.assertIn("status=ok", out_with)
        self.assertNotIn("ai_cli_not_on_path", out_with)
        self.assertIn("ai_cli_check=skipped", out_with)
        self.assertIn("host_mode=maf", out_with)

    def test_host_mode_still_reports_a_damaged_install(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td).resolve()
            _install(target)
            damaged = target / ".claude" / "skills" / "quality-playbook" / "quality_gate.py"
            damaged.unlink()
            with mock.patch.object(v.shutil, "which", _without_claude_on_path()):
                rc, out = _run_main([str(target), "--host-mode", "maf"])
        self.assertNotEqual(rc, 0, out)
        self.assertIn("finding=install_partial", out)
        self.assertNotIn("ai_cli_not_on_path", out)

    def test_host_mode_still_reports_missing_scaffolding(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td).resolve()
            _install(target)
            with mock.patch.object(v.shutil, "which", _without_claude_on_path()):
                rc, out = _run_main([str(target), "--host-mode", "maf"])
        self.assertNotEqual(rc, 0, out)
        self.assertIn("scaffolding_missing", out)

    def test_an_unknown_host_mode_is_refused(self) -> None:
        with TemporaryDirectory() as td, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                v.main([td, "--host-mode", "something-else"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
