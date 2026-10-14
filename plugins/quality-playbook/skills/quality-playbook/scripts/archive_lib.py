"""archive_lib.py — shared helpers for quality/ run archival and INDEX rendering.

Implements the Phase 5c contract from QPB_v1.5.1_Design.md:

- `write_timestamped_result(quality_dir, basename, content)` writes
  `quality/results/<basename>-YYYYMMDDTHHMMSSZ.<ext>` plus a `<basename>-latest.<ext>`
  pointer (symlink on POSIX, copy fallback on Windows).
- `archive_run(repo_dir, timestamp, *, status)` snapshots the live `quality/`
  tree into `quality/previous_runs/<timestamp>[-FAILED]/`, writes a per-run `INDEX.md`,
  and appends one row to `quality/RUN_INDEX.md`. Status `"success"` uses no
  suffix; `"failed"` and `"partial"` produce `-FAILED` / `-PARTIAL` suffixes.
- `render_index_markdown`, `render_run_index_row`, `render_run_index_header`,
  `append_run_index_row` — rendering primitives shared with
  `bin/migrate_v1_5_0_layout.py`.
- `build_index_payload(repo_dir, run_folder)` — best-effort §11 payload for
  any run folder (live or archived), reading git log + surviving artifacts.

CLI: operator-driven archive for failed or partial runs. Adopters invoke
this via `python -m bin.quality_playbook archive` (the operator-facing
entry point dispatches here); direct `python -m bin.archive_lib` also
works and is equivalent. The orchestrator calls `archive_run` directly
at end of a successful Phase 6 — the CLI is only needed to preserve
non-successful runs before the next run's overwrite.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SEVERITY_LITERALS = ("HIGH", "MEDIUM", "LOW")
DISPOSITION_LITERALS = (
    "code-fix",
    "spec-fix",
    "upstream-spec-issue",
    "mis-read",
    "deferred",
)
TIER_LITERALS = ("1", "2", "3", "4", "5", "unknown")
# v1.5.4 Phase 3.6.2 (B-19): the `-PARTIAL` filename suffix is retired
# in favour of an in-archive `.partial` sentinel file. This keeps run
# IDs derivable from a single timestamp (no suffix discrimination
# downstream) while still flagging interrupted runs to consumers.
# `-FAILED` stays — it signals an archived run with a definite gate
# fail, distinct from "interrupted before Phase 6 finalization".
STATUS_SUFFIX = {"success": "", "failed": "-FAILED", "partial": ""}

# v1.5.4 Phase 3.6.2 (B-19): the canonical archive directory name
# under each target's `quality/`. Migrated from `runs/` to
# `previous_runs/`. Legacy `quality/runs/` archives remain readable
# for backward-compat but new archives land here.
ARCHIVE_DIRNAME = "previous_runs"
LEGACY_ARCHIVE_DIRNAME = "runs"

# Sentinel file written inside an archive folder when the prior run
# was interrupted (no Phase-6 finalization). Replaces the `-PARTIAL`
# filename suffix.
PARTIAL_SENTINEL_NAME = ".partial"

_VERSION_HEADER_PATTERN = re.compile(r"Quality Playbook v([0-9]+(?:\.[0-9]+)+)", re.IGNORECASE)
# v1.5.7 089d (F22): the canonical BUG-NNN heading pattern lives in
# `bin/run_state_lib.BUG_HEADING_PATTERN_RE` (see that constant for
# the rationale + scope). archive_lib re-exports it via this local
# alias to preserve the existing name (avoids touching ~30 call
# sites of `_BUG_HEADING_PATTERN`).
#
# v1.5.7 090c: foreign-bin-proof import. `from bin.run_state_lib`
# succeeds when this runs as `python -m bin.archive_lib` from the
# clone, but a script-form invocation (or any context where `bin/`
# isn't a package on sys.path) hits ImportError. The fallback
# path-loads `run_state_lib.py` from the SAME directory as this
# file — anchored on `Path(__file__)` so it can never resolve to a
# foreign sibling repo's `bin/`.
try:
    from bin.run_state_lib import (
        BUG_HEADING_PATTERN_RE as _BUG_HEADING_PATTERN,
    )
except ImportError:
    import importlib.util as _ilu
    _rsl_path = Path(__file__).resolve().parent / "run_state_lib.py"
    _rsl_spec = _ilu.spec_from_file_location(
        "_qpb_run_state_lib_via_archive_lib", _rsl_path,
    )
    if _rsl_spec is None or _rsl_spec.loader is None:
        raise ImportError(
            f"archive_lib: cannot resolve run_state_lib — "
            f"`from bin import` failed and path-load fallback "
            f"target {_rsl_path} is missing."
        )
    _rsl_mod = _ilu.module_from_spec(_rsl_spec)
    # v1.5.7 090c: register in sys.modules BEFORE exec_module so
    # any dataclass/typing machinery inside run_state_lib that
    # consults `sys.modules[__module__]` finds the module. Without
    # this, dataclasses.field() raises AttributeError because
    # `cls.__module__` is the private namespaced name but
    # `sys.modules` has no entry for it. The 089u/089v shim's
    # `_load_bundled_script` has the same shape but works because
    # install_skill (the only loaded module) does not use
    # dataclasses; this script does.
    sys.modules[_rsl_spec.name] = _rsl_mod
    _rsl_spec.loader.exec_module(_rsl_mod)
    _BUG_HEADING_PATTERN = _rsl_mod.BUG_HEADING_PATTERN_RE
_REQ_HEADING_PATTERN = re.compile(r"^###\s+REQ-([A-Za-z0-9]+)", re.MULTILINE)
_SEVERITY_PATTERN = re.compile(r"\*\*Severity\*\*\s*[:.-]\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE)
_PHASE_CHECK_PATTERN = re.compile(r"^-\s*\[x\]\s*Phase\s*([0-9a-zA-Z]+)", re.MULTILINE)
# v1.5.7 089d (F18): the canonical gate output source is
# `quality/results/quality-gate.log` (gate stdout captured by
# run_playbook._finalize_iteration). The v1.5.7 gate emits one of
# three lines:
#     RESULT: GATE PASSED
#     RESULT: GATE PASSED WITH CLEANUP NEEDED — N audit record-keeping gap(s)
#     RESULT: GATE FAILED — N substantive issue(s) must be fixed
# Group 1 captures the verdict tail; _GATE_RESULT_TO_VERDICT maps it
# to the schemas.md §11 gate_verdict enum value (incl. the F17
# "pass-with-cleanup" value). PASSED-WITH-CLEANUP-NEEDED is listed
# first so longest-match wins (avoid mis-matching "PASSED" inside
# "PASSED WITH CLEANUP NEEDED"). Pre-089d this pattern read
# `gate_result: 'PASS'` key=value (zero matches on v1.5.7 output —
# Mode B archive wrote gate_verdict: "unknown" for every run, which
# the validator then rejected).
_GATE_RESULT_PATTERN = re.compile(
    r"^RESULT:\s+GATE\s+(PASSED WITH CLEANUP NEEDED|PASSED|FAILED)\b",
    re.MULTILINE,
)

# Legacy `gate_result: 'PASS|FAIL|WARN'` key=value form. Pre-v1.5.7
# archives stored this in run-*.json / gate-report-latest.json. Kept
# strictly for back-compat — v1.5.7 runs hit the new pattern above
# against quality-gate.log first.
_GATE_RESULT_LEGACY_PATTERN = re.compile(
    r"gate_result['\"]?\s*[:=]\s*['\"]?(PASS|FAIL|WARN)['\"]?",
    re.IGNORECASE,
)

# Unified verdict mapping. v1.5.7 verbatim tokens
# ("PASSED" / "PASSED WITH CLEANUP NEEDED" / "FAILED") use the F17
# enum values; legacy tokens ("PASS" / "FAIL" / "WARN") map to the
# pre-F17 enum values for back-compat with archived runs.
_GATE_RESULT_TO_VERDICT = {
    # v1.5.7 (089d F18) — quality-gate.log shapes:
    "PASSED": "pass",
    "PASSED WITH CLEANUP NEEDED": "pass-with-cleanup",
    "FAILED": "fail",
    # Legacy (pre-v1.5.7) — run-*.json key=value shapes:
    "PASS": "pass",
    "FAIL": "fail",
    "WARN": "partial",
}


class ArchiveError(Exception):
    """Raised on unrecoverable archive failures."""


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def utc_compact_timestamp(now: Optional[datetime] = None) -> str:
    """Return `YYYYMMDDTHHMMSSZ` — basic ISO 8601 timestamp, UTC.

    Used for folder names (quality/previous_runs/<ts>/) and file names under
    quality/results/.
    """
    dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def utc_extended_timestamp(now: Optional[datetime] = None) -> str:
    """Return `YYYY-MM-DDTHH:MM:SSZ` — extended ISO 8601, UTC, second precision."""
    dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


_COMPACT_TS_PATTERN = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")


def extended_from_compact(ts: str) -> str:
    """Convert `YYYYMMDDTHHMMSSZ` to `YYYY-MM-DDTHH:MM:SSZ`.

    Returns the input unchanged when it does not match the compact pattern
    (defensive for callers that pass already-extended or arbitrary tokens).
    """
    if not isinstance(ts, str):
        return ts
    m = _COMPACT_TS_PATTERN.match(ts)
    if not m:
        return ts
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}Z"


def compact_from_extended(ts: str) -> Optional[str]:
    """Convert extended ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`) to compact.

    Returns the input unchanged when it is already compact, or `None` when it
    does not parse as ISO 8601.
    """
    if not isinstance(ts, str) or not ts:
        return None
    if _COMPACT_TS_PATTERN.match(ts):
        return ts
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
    return dt.strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# write_timestamped_result
# ---------------------------------------------------------------------------


def _split_basename_ext(basename: str) -> Tuple[str, str]:
    """Split `foo` or `foo.json` into `(stem, ext_with_dot_or_empty)`."""
    if "." in basename and not basename.startswith("."):
        stem, _, ext = basename.rpartition(".")
        return stem, "." + ext
    return basename, ""


def write_timestamped_result(
    quality_dir: Path,
    basename: str,
    content: str,
    *,
    now: Optional[datetime] = None,
) -> Tuple[Path, Path]:
    """Write a timestamped result file + a `-latest` pointer.

    Arguments:
      quality_dir — the run's quality/ directory; the result goes under
                    quality_dir / "results".
      basename    — name with or without extension. `foo.json` writes to
                    `results/foo-<ts>.json` + `results/foo-latest.json`.
                    Extensionless `foo` writes `results/foo-<ts>` + `results/foo-latest`.
      content     — text written to the timestamped path.

    Returns `(timestamped_path, latest_path)`. `latest_path` is a symlink on
    POSIX and a copy on platforms that reject symlinks.
    """
    stem, ext = _split_basename_ext(basename)
    ts = utc_compact_timestamp(now)
    results_dir = Path(quality_dir) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamped = results_dir / f"{stem}-{ts}{ext}"
    latest = results_dir / f"{stem}-latest{ext}"
    timestamped.write_text(content, encoding="utf-8")

    if latest.exists() or latest.is_symlink():
        try:
            latest.unlink()
        except OSError:
            pass
    target_name = timestamped.name
    try:
        os.symlink(target_name, latest)
    except (OSError, NotImplementedError):
        shutil.copyfile(timestamped, latest)
    return timestamped, latest


# ---------------------------------------------------------------------------
# Content extraction for INDEX.md payloads (shared with migration script)
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _git_available(repo: Path) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return True


def _git_log_timestamps(repo: Path, folder: Path) -> Tuple[Optional[str], Optional[str]]:
    try:
        rel = folder.relative_to(repo).as_posix()
    except ValueError:
        return None, None
    try:
        proc = subprocess.run(
            ["git", "log", "--reverse", "--format=%aI", "--", rel],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None, None
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        return None, None
    return lines[0], lines[-1]


def _git_head_sha(repo: Path) -> str:
    if not _git_available(repo):
        return "unknown"
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
    except subprocess.CalledProcessError:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def _fs_mtimes(folder: Path) -> Tuple[str, str]:
    mtimes: List[float] = []
    for path in folder.rglob("*"):
        if path.is_file():
            try:
                mtimes.append(path.stat().st_mtime)
            except OSError:
                continue
    if not mtimes:
        try:
            stat = folder.stat()
            mtimes.append(stat.st_mtime)
        except OSError:
            now = utc_extended_timestamp()
            return now, now
    first = datetime.fromtimestamp(min(mtimes), tz=timezone.utc).replace(microsecond=0)
    last = datetime.fromtimestamp(max(mtimes), tz=timezone.utc).replace(microsecond=0)
    return first.isoformat().replace("+00:00", "Z"), last.isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_seconds(start: str, end: str) -> int:
    a = _parse_iso(start)
    b = _parse_iso(end)
    if a is None or b is None:
        return 0
    # v1.5.6 fix-up 071: _parse_iso returns UTC-aware for ISO strings
    # with a Z suffix or +HH:MM offset, but naive for bare ISO strings
    # like "2026-05-08T12:34:56". Mixing naive and aware raises
    # TypeError on subtraction. Normalize both to UTC-aware so
    # downstream consumers (write_live_index_final, _resolve_bounds)
    # don't crash on heterogeneous timestamp inputs.
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return max(int((b - a).total_seconds()), 0)


def _resolve_bounds(repo: Path, folder: Path) -> Tuple[str, str, int]:
    start: Optional[str] = None
    end: Optional[str] = None
    if _git_available(repo):
        start, end = _git_log_timestamps(repo, folder)
    if start is None or end is None:
        fs_start, fs_end = _fs_mtimes(folder)
        start = start or fs_start
        end = end or fs_end
    return start, end, _duration_seconds(start, end)


def _extract_qpb_version(run_folder: Path) -> str:
    for name in ("BUGS.md", "REQUIREMENTS.md", "PROGRESS.md", "QUALITY.md"):
        for prefix in (run_folder / "quality", run_folder):
            text = _read_text(prefix / name)
            if not text:
                continue
            match = _VERSION_HEADER_PATTERN.search(text)
            if match:
                return match.group(1)
    return "unknown"


def _split_by_heading(text: str, pattern: re.Pattern) -> List[str]:
    positions = [m.start() for m in pattern.finditer(text)]
    if not positions:
        return []
    positions.append(len(text))
    return [text[positions[i]:positions[i + 1]] for i in range(len(positions) - 1)]


def _extract_bug_counts(run_folder: Path) -> Dict[str, int]:
    text = _read_text(run_folder / "quality" / "BUGS.md") or _read_text(run_folder / "BUGS.md")
    counts: Dict[str, int] = {level: 0 for level in SEVERITY_LITERALS}
    counts.update({d: 0 for d in DISPOSITION_LITERALS})
    if not text:
        return counts
    for segment in _split_by_heading(text, _BUG_HEADING_PATTERN):
        sev_match = _SEVERITY_PATTERN.search(segment)
        if sev_match:
            counts[sev_match.group(1).upper()] += 1
        for disposition in DISPOSITION_LITERALS:
            if re.search(
                rf"\*\*disposition\*\*\s*[:.-]\s*{re.escape(disposition)}",
                segment,
                re.IGNORECASE,
            ):
                counts[disposition] += 1
    return counts


def _extract_req_tier_counts(run_folder: Path) -> Dict[str, int]:
    text = _read_text(run_folder / "quality" / "REQUIREMENTS.md") or _read_text(
        run_folder / "REQUIREMENTS.md"
    )
    counts: Dict[str, int] = {tier: 0 for tier in TIER_LITERALS}
    if not text:
        return counts
    for segment in _split_by_heading(text, _REQ_HEADING_PATTERN):
        # v1.5.7 Issue 3 (chi-surfaced) — conceptually-equivalent
        # instance of the Artifact-Summary tier-count drift. The prior
        # pattern `\*\*Tier\*\*\s*[:.-]\s*([1-5])` only matched the
        # legacy `**Tier**: N` form (colon OUTSIDE the bold markers).
        # The canonical REQ-record prose is `- **Tier:** N` (colon
        # INSIDE the bold), so every record fell to the `unknown`
        # bucket — chi-1.5.1's 16 Tier-3 REQs all counted as unknown
        # in the INDEX.md `summary.requirements` payload. The `:?`
        # before `\*\*` plus the optional `[:.-]?` tolerate both forms
        # without a schema change.
        tier_match = re.search(
            r"\*\*Tier:?\*\*\s*[:.-]?\s*([1-5])", segment, re.IGNORECASE
        )
        if tier_match:
            counts[tier_match.group(1)] += 1
        else:
            counts["unknown"] += 1
    return counts


def _extract_phases_executed(run_folder: Path) -> List[Dict[str, str]]:
    text = _read_text(run_folder / "quality" / "PROGRESS.md") or _read_text(run_folder / "PROGRESS.md")
    if not text:
        return []
    return [
        {
            "phase_id": m.group(1),
            "model": "unknown",
            "start": "unknown",
            "end": "unknown",
            "exit_status": "unknown",
        }
        for m in _PHASE_CHECK_PATTERN.finditer(text)
    ]


def _extract_gate_verdict(run_folder: Path) -> str:
    results_dir = run_folder / "quality" / "results"
    if results_dir.is_dir():
        # v1.5.7 089d (F18): the canonical v1.5.7 source is the
        # captured gate stdout at quality-gate.log; it carries one
        # of three `RESULT: GATE …` lines that _GATE_RESULT_PATTERN
        # matches. Pre-089d this function only looked at run-*.json
        # / gate-report-latest.json for a `gate_result: 'PASS'`
        # key=value form that v1.5.7 never emits, so Mode B archive
        # wrote gate_verdict: "unknown" → validator rejected it.
        gate_log = results_dir / "quality-gate.log"
        if gate_log.is_file():
            match = _GATE_RESULT_PATTERN.search(_read_text(gate_log))
            if match:
                return _GATE_RESULT_TO_VERDICT.get(
                    match.group(1).upper(), "partial",
                )
        # Legacy fallback: pre-v1.5.7 archives stored the verdict in
        # run-*.json / gate-report-latest.json key=value JSON form.
        # _GATE_RESULT_LEGACY_PATTERN matches those; the unified
        # _GATE_RESULT_TO_VERDICT map handles both vocabularies.
        for candidate in sorted(results_dir.glob("run-*.json")):
            match = _GATE_RESULT_LEGACY_PATTERN.search(
                _read_text(candidate)
            )
            if match:
                return _GATE_RESULT_TO_VERDICT.get(
                    match.group(1).upper(), "partial",
                )
        latest = results_dir / "gate-report-latest.json"
        if latest.is_file():
            raw = _read_text(latest)
            match = _GATE_RESULT_LEGACY_PATTERN.search(raw)
            if match:
                return _GATE_RESULT_TO_VERDICT.get(
                    match.group(1).upper(), "partial",
                )
    progress = _read_text(run_folder / "quality" / "PROGRESS.md") or _read_text(
        run_folder / "PROGRESS.md"
    )
    if "Terminal Gate Verification" in progress:
        tail = progress[progress.find("Terminal Gate"):]
        if re.search(r"gate_result\s*[:.-]?\s*pass|\bPASS\b", tail):
            return "pass"
    return "unknown"


def _collect_artifacts(run_folder: Path) -> List[str]:
    artifacts: List[str] = []
    for path in sorted(run_folder.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "INDEX.md" and path.parent == run_folder:
            continue
        try:
            artifacts.append(path.relative_to(run_folder).as_posix())
        except ValueError:
            continue
    return artifacts


def build_index_payload(
    repo: Path,
    run_folder: Path,
    *,
    target_repo_path: str = ".",
    target_role_breakdown: Optional[Dict[str, object]] = None,
    target_repo_git_sha: Optional[str] = None,
    gate_verdict_override: Optional[str] = None,
    invocation_flags: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Assemble the §11 `INDEX.md` payload for an archived or live run folder.

    Fields that cannot be recovered from git log or the surviving artifacts
    are stored as the literal string `"unknown"`. ``target_role_breakdown``
    is the v1.5.4 replacement for the v1.5.3 ``target_project_type`` field;
    it carries the breakdown subtree of ``quality/exploration_role_map.json``
    (or ``None`` if Phase 1 hasn't produced a role map yet).

    ``invocation_flags`` is an additive v1.5.1 field (Council — gpt-5.4
    blocker 2) that captures run-configuration flags a later auditor needs
    to interpret the artifacts — today just ``no_formal_docs`` per Item 1.3.
    Defaults to ``{"no_formal_docs": False}`` when not supplied. The key
    is additive relative to schemas.md §11 required fields, so
    quality_gate's invariant #10 continues to pass unchanged.
    """
    start, end, duration = _resolve_bounds(repo, run_folder)
    verdict = gate_verdict_override or _extract_gate_verdict(run_folder)
    if verdict not in ("pass", "fail", "partial"):
        verdict = "partial"
    merged_flags: Dict[str, object] = {"no_formal_docs": False}
    if invocation_flags:
        merged_flags.update(invocation_flags)
    # v1.5.4 Round 2 Council Step 5 polish: pull the canonical INDEX
    # schema_version from bin.role_map so the two bin-side emission
    # sites (here and run_playbook.write_live_index_stub) cannot drift
    # against each other on a future schema bump.
    from . import role_map as _role_map  # noqa: WPS433
    return {
        # v1.5.4 Part 1 / Round 1 Council finding C2-1: explicit INDEX
        # schema_version routes the gate between the legacy
        # target_project_type contract (1.0, archived runs) and the
        # current target_role_breakdown contract (2.0, current runs).
        # See schemas.md §11 and the v1.5.4 Design Part 1.
        "schema_version": _role_map.INDEX_SCHEMA_VERSION_CURRENT,
        "run_timestamp_start": start,
        "run_timestamp_end": end,
        "duration_seconds": duration,
        "qpb_version": _extract_qpb_version(run_folder),
        "target_repo_path": target_repo_path,
        "target_repo_git_sha": target_repo_git_sha or _git_head_sha(repo),
        "target_role_breakdown": target_role_breakdown,
        "phases_executed": _extract_phases_executed(run_folder),
        "summary": {
            "requirements": _extract_req_tier_counts(run_folder),
            "bugs": _extract_bug_counts(run_folder),
            "gate_verdict": verdict,
        },
        "artifacts": _collect_artifacts(run_folder),
        "invocation_flags": merged_flags,
    }


# ---------------------------------------------------------------------------
# INDEX.md / RUN_INDEX.md rendering
# ---------------------------------------------------------------------------


def render_index_markdown(run_id: str, payload: Dict[str, object], *, provenance: str) -> str:
    """Render the per-run `INDEX.md`.

    `provenance` is a short sentence explaining who wrote the file. For
    migration this is "backfilled by bin/migrate_v1_5_0_layout.py"; for
    archive_run it is "written by bin/archive_lib.archive_run".
    """
    body = json.dumps(payload, indent=2, sort_keys=False)
    return (
        f"# Run Index — {run_id}\n\n"
        f"Playbook run archived to `quality/{ARCHIVE_DIRNAME}/{run_id}/`. This file was\n"
        f"{provenance}. Fields marked `\"unknown\"` could not be recovered\n"
        "from the run's artifacts.\n\n"
        "```json\n"
        f"{body}\n"
        "```\n"
    )


def render_run_index_header() -> str:
    return (
        "# QPB RUN_INDEX\n\n"
        f"Append-only index of every archived run under `quality/{ARCHIVE_DIRNAME}/`. One row\n"
        "per archived run. Maintained by `bin/migrate_v1_5_0_layout.py` at\n"
        "migration time and by `bin/archive_lib.archive_run` at end of every\n"
        "successful run. Rows are never rewritten; a run's `INDEX.md` is the\n"
        "authoritative per-run record. The Role breakdown column summarises\n"
        "the four shares from `quality/exploration_role_map.json` (skill /\n"
        "code / tool / other) — `n/a` when Phase 1 produced no role map.\n\n"
        "| Run | QPB version | Role breakdown | Gate verdict | Bug count | Per-run INDEX |\n"
        "|-----|-------------|----------------|--------------|-----------|----------------|\n"
    )


def _format_role_breakdown_summary(payload: Dict[str, object]) -> str:
    """Render the role breakdown into the compact RUN_INDEX cell. Falls
    back to ``n/a`` when the field is absent or the breakdown carries no
    percentages (e.g. stub INDEX written before Phase 1 produced the
    role map)."""
    breakdown = payload.get("target_role_breakdown")
    if not isinstance(breakdown, dict):
        return "n/a"
    pcts = breakdown.get("percentages")
    if not isinstance(pcts, dict):
        return "n/a"
    return (
        f"skill {float(pcts.get('skill_share', 0)) * 100:.0f}% / "
        f"code {float(pcts.get('code_share', 0)) * 100:.0f}% / "
        f"tool {float(pcts.get('tool_share', 0)) * 100:.0f}% / "
        f"other {float(pcts.get('other_share', 0)) * 100:.0f}%"
    )


def render_run_index_row(
    run_id: str,
    payload: Dict[str, object],
    *,
    archive_dir: str = ARCHIVE_DIRNAME,
) -> str:
    """Render one RUN_INDEX.md row.

    ``archive_dir`` defaults to the current canonical name
    (``previous_runs``); legacy callers (e.g.
    :mod:`bin.migrate_v1_5_0_layout`, which lands archives under the
    pre-v1.5.4 ``runs/`` directory) pass ``LEGACY_ARCHIVE_DIRNAME``
    so the navigation link points at the actual on-disk location."""
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    bugs = summary.get("bugs") if isinstance(summary.get("bugs"), dict) else {}
    bug_count = sum(int(bugs.get(s, 0)) for s in SEVERITY_LITERALS if isinstance(bugs.get(s, 0), int))
    return (
        f"| {run_id} "
        f"| {payload.get('qpb_version', 'unknown')} "
        f"| {_format_role_breakdown_summary(payload)} "
        f"| {summary.get('gate_verdict', 'partial')} "
        f"| {bug_count} "
        f"| [INDEX.md](quality/{archive_dir}/{run_id}/INDEX.md) |"
    )


def append_run_index_row(repo_dir: Path, run_id: str, payload: Dict[str, object]) -> Path:
    """Append one row to quality/RUN_INDEX.md (never rewrite prior rows).

    Creates the file with a header if it does not exist. If the row for
    `run_id` is already present, leaves the file untouched (idempotent).
    """
    path = Path(repo_dir) / "quality" / "RUN_INDEX.md"
    row = render_run_index_row(run_id, payload)
    existing = _read_text(path)
    if existing:
        if f"| {run_id} " in existing:
            return path
        content = existing.rstrip() + "\n" + row + "\n"
    else:
        content = render_run_index_header() + row + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def load_index_payload(path: Path) -> Optional[Dict[str, object]]:
    """Parse the JSON block out of a per-run INDEX.md, returning the payload dict."""
    text = _read_text(path)
    if not text:
        return None
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# archive_run — end-of-run snapshot
# ---------------------------------------------------------------------------


def _runs_exclude_ignore(*_: object) -> set:
    """Passed to copytree's `ignore=` to exclude both archive
    directories — current (``previous_runs/``) and legacy (``runs/``)
    — from recursive inclusion in a fresh archive. v1.5.4 Phase 3.6.2
    (B-19, H2 fix): without ignoring the current archive dir, every
    new archive would recursively include the prior archive tree and
    grow unbounded."""
    return {ARCHIVE_DIRNAME, LEGACY_ARCHIVE_DIRNAME}


def compute_archive_timestamp(
    quality_dir: Path, *, now: Optional[datetime] = None
) -> str:
    """Derive the archive timestamp for the existing live `quality/`
    tree.

    v1.5.4 Phase 3.6.2 (B-19, M8 fix): pin to the prior run's
    ``run_timestamp_end`` (the field captured at end-of-Phase-6),
    NOT ``run_timestamp_start``. The end-time is the meaningful
    archival anchor — it's when the artifacts in the live tree were
    finalized. Fallback chain:

      1. ``quality/INDEX.md``'s ``run_timestamp_end`` (compact form).
      2. ``quality/BUGS.md`` mtime (the most recently-touched
         canonical artifact when INDEX is missing/malformed).
      3. Current UTC time (final fallback when both above are absent).
    """
    index_path = quality_dir / "INDEX.md"
    if index_path.is_file():
        payload = load_index_payload(index_path)
        if isinstance(payload, dict):
            ts = payload.get("run_timestamp_end")
            if isinstance(ts, str) and ts:
                try:
                    return compact_from_extended(ts)
                except Exception:  # noqa: BLE001 — defensive parse fallback
                    pass
    bugs_md = quality_dir / "BUGS.md"
    if bugs_md.is_file():
        try:
            mtime = datetime.fromtimestamp(
                bugs_md.stat().st_mtime, tz=timezone.utc
            )
            return mtime.strftime("%Y%m%dT%H%M%SZ")
        except OSError:
            pass
    if now is None:
        now = datetime.now(tz=timezone.utc)
    return now.strftime("%Y%m%dT%H%M%SZ")


def archive_run(
    repo_dir: Path,
    timestamp: str,
    *,
    status: str = "success",
    target_repo_path: str = ".",
    target_role_breakdown: Optional[Dict[str, object]] = None,
    gate_verdict_override: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Path:
    """Snapshot quality/ into quality/previous_runs/<timestamp>[-FAILED]/,
    write INDEX.md, append RUN_INDEX.md row.

    v1.5.4 Phase 3.6.2 (B-19): the archive destination migrated from
    ``quality/runs/`` to ``quality/previous_runs/``. The ``-PARTIAL``
    filename suffix was retired in favour of an in-archive
    ``.partial`` sentinel file (``status="partial"`` writes
    ``<archive>/.partial`` rather than appending ``-PARTIAL`` to the
    folder name). ``-FAILED`` remains as a folder-name suffix because
    it represents a definite gate-failed run, not an interrupted one.

    Arguments:
      repo_dir — target repo root.
      timestamp — run start timestamp, basic ISO 8601 (YYYYMMDDTHHMMSSZ).
      status — one of "success" (no suffix), "failed" (-FAILED suffix),
               "partial" (no suffix; .partial sentinel written inside).
      target_role_breakdown — v1.5.4 INDEX field; the breakdown subtree
               of `quality/exploration_role_map.json`. Auto-loaded from
               the repo if not supplied; pass ``None`` explicitly to
               skip loading.
      gate_verdict_override — force a specific gate_verdict value when the
               caller already knows the outcome (end-of-run hook path).

    Returns the archive folder path. Leaves the live `quality/` tree in
    place so the next run can either continue from it or overwrite.
    """
    if status not in STATUS_SUFFIX:
        raise ArchiveError(f"invalid status {status!r}; expected success/failed/partial")
    repo_dir = Path(repo_dir)
    quality_dir = repo_dir / "quality"
    if not quality_dir.is_dir():
        raise ArchiveError(f"{quality_dir} does not exist; nothing to archive")

    run_id = timestamp + STATUS_SUFFIX[status]
    archive_root = quality_dir / ARCHIVE_DIRNAME / run_id
    if archive_root.exists():
        raise ArchiveError(
            f"archive target {archive_root} already exists; refusing to overwrite "
            "(invoke with a different timestamp or remove the existing folder first)"
        )
    archive_root.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = quality_dir / ARCHIVE_DIRNAME / (run_id + ".staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    shutil.copytree(
        quality_dir,
        staging_dir / "quality",
        # v1.5.4 Phase 3.6.2 H2 fix: exclude BOTH the current and
        # legacy archive dirs so a fresh archive doesn't recursively
        # include the prior archive tree and grow unbounded.
        ignore=shutil.ignore_patterns(ARCHIVE_DIRNAME, LEGACY_ARCHIVE_DIRNAME),
    )
    staging_dir.rename(archive_root)
    # v1.5.4 Phase 3.6.2 (B-19): drop a ``.partial`` sentinel inside
    # the archive folder when the prior run was interrupted. Replaces
    # the ``-PARTIAL`` filename suffix.
    if status == "partial":
        (archive_root / PARTIAL_SENTINEL_NAME).write_text(
            "Prior run was archived as partial: no Phase-6 finalization "
            "captured. Treat artifacts as incomplete.\n",
            encoding="utf-8",
        )

    # Build the INDEX.md payload using the freshly-archived copy so subsequent
    # git log operations see its content (it's staged but not committed yet).
    status_verdict = {
        "success": "pass",
        "failed": "fail",
        "partial": "partial",
    }[status]
    effective_override = gate_verdict_override or status_verdict
    if target_role_breakdown is None:
        # Auto-discover the live role map from quality/. Avoid a top-level
        # import cycle: archive_lib has no other dependency on role_map.
        from . import role_map as _role_map  # noqa: WPS433
        loaded = _role_map.load_role_map(_role_map.default_path(repo_dir))
        target_role_breakdown = _role_map.role_breakdown_for_index(loaded)
    payload = build_index_payload(
        repo_dir,
        archive_root,
        target_repo_path=target_repo_path,
        target_role_breakdown=target_role_breakdown,
        gate_verdict_override=effective_override,
    )
    index_path = archive_root / "INDEX.md"
    index_path.write_text(
        render_index_markdown(
            run_id,
            payload,
            provenance="written by `bin/archive_lib.archive_run` at end of run",
        ),
        encoding="utf-8",
    )
    append_run_index_row(repo_dir, run_id, payload)
    return archive_root


# ---------------------------------------------------------------------------
# Compatibility fork (CC-03): mechanical Phase 6 gate-verdict finalization
# ---------------------------------------------------------------------------
# Upstream v1.6.0 left the Mode A INDEX update to the agent ("Phase 6 MUST
# have updated it") without saying who maps the verdict or how. The
# fork makes the mapping mechanical: the parent runs the gate, then this
# helper maps the LAST `RESULT: GATE …` line of the receipted gate log
# through `_GATE_RESULT_TO_VERDICT` into `summary.gate_verdict`. The
# fresh-context auditor re-derives the same mapping from the RESULT line
# it witnesses and FAILs on any mismatch.

GATE_LOG_RELPATH = Path("quality") / "results" / "quality-gate.log"
_INDEX_JSON_BLOCK = re.compile(r"(```json\n)(.*?)(\n```)", re.DOTALL)


def read_last_gate_result(gate_log: Path) -> Optional[str]:
    """Return the verdict token of the LAST `RESULT: GATE …` line in
    ``gate_log`` (``"PASSED"``, ``"PASSED WITH CLEANUP NEEDED"`` or
    ``"FAILED"``), or ``None`` when the log is absent or carries no
    RESULT line. The last line wins so a log that accumulated more than
    one gate run reports the most recent verdict."""
    matches = _GATE_RESULT_PATTERN.findall(_read_text(Path(gate_log)))
    return matches[-1].upper() if matches else None


def gate_verdict_from_result(token: str) -> str:
    """Map a gate RESULT token to the schemas.md §11 INDEX enum value."""
    try:
        return _GATE_RESULT_TO_VERDICT[token.upper()]
    except KeyError:
        raise ArchiveError(f"unrecognised gate RESULT token {token!r}") from None


def finalize_index_gate_verdict(
    repo_dir: Path,
    *,
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """Write the Phase 6 gate verdict into the live ``quality/INDEX.md``.

    Reads the last ``RESULT: GATE …`` line of
    ``quality/results/quality-gate.log``, maps it to the INDEX enum,
    and rewrites the fenced JSON block in place with
    ``summary.gate_verdict``, ``run_timestamp_end`` and
    ``duration_seconds`` updated. Text outside the JSON block is left
    untouched. Raises :class:`ArchiveError` (and writes nothing) when
    the gate log has no RESULT line or INDEX.md has no parseable JSON
    object — the verdict is never guessed.

    Returns ``{"result": <token>, "gate_verdict": <enum>,
    "run_timestamp_end": <ts>, "duration_seconds": <int>}``.
    """
    repo_dir = Path(repo_dir)
    gate_log = repo_dir / GATE_LOG_RELPATH
    token = read_last_gate_result(gate_log)
    if token is None:
        raise ArchiveError(
            f"{gate_log}: no `RESULT: GATE …` line — run the gate "
            "(`python3 quality_gate.py . > quality/results/quality-gate.log 2>&1`) "
            "before finalizing INDEX.md"
        )
    verdict = gate_verdict_from_result(token)
    index_path = repo_dir / "quality" / "INDEX.md"
    text = _read_text(index_path)
    match = _INDEX_JSON_BLOCK.search(text)
    if not match:
        raise ArchiveError(f"{index_path}: missing or has no fenced ```json block")
    try:
        payload = json.loads(match.group(2))
    except json.JSONDecodeError as exc:
        raise ArchiveError(f"{index_path}: fenced JSON invalid ({exc})") from None
    if not isinstance(payload, dict):
        raise ArchiveError(f"{index_path}: fenced JSON block is not an object")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        summary = {}
        payload["summary"] = summary
    summary["gate_verdict"] = verdict
    end = utc_extended_timestamp(now)
    payload["run_timestamp_end"] = end
    duration = _duration_seconds(str(payload.get("run_timestamp_start", "")), end)
    payload["duration_seconds"] = duration
    body = json.dumps(payload, indent=2, sort_keys=False)
    new_text = text[: match.start(2)] + body + text[match.end(2):]
    index_path.write_text(new_text, encoding="utf-8")
    return {
        "result": token,
        "gate_verdict": verdict,
        "run_timestamp_end": end,
        "duration_seconds": duration,
    }


# ---------------------------------------------------------------------------
# Per-project AGENTS.md (v1.5.4 Phase 3.6.5 B-17; moved here by the
# compatibility fork, CC-15)
# ---------------------------------------------------------------------------
# The generator previously lived in bin/run_playbook.py, which is not in
# the install bundle, so Mode A had no sanctioned way to produce the
# AGENTS.md the gate requires. It now lives in this bundled module;
# run_playbook keeps its historical private names as aliases.
#
# v1.5.4 Phase 3.7 Fix 3 (Round 8 HIGH): the sentinel constant carries
# the literal version (so an operator inspecting the file knows which
# QPB version produced it), but detection uses a PREFIX match. v1.5.5+
# will correctly recognise v1.5.4-generated AGENTS.md as QPB-managed
# and regenerate them rather than preserving them as if operator-
# authored. The prefix is the load-bearing part; the version after
# `QPB ` is informational only.
QPB_AGENTS_SENTINEL_PREFIX = "<!-- generated by QPB"
QPB_AGENTS_SENTINEL = f"{QPB_AGENTS_SENTINEL_PREFIX} v1.5.4 -->"


def _load_role_map_module():
    try:
        from . import role_map as _role_map  # noqa: WPS433
    except ImportError:
        import importlib.util as _ilu
        _rm_path = Path(__file__).resolve().parent / "role_map.py"
        _rm_spec = _ilu.spec_from_file_location(
            "_qpb_role_map_via_archive_lib", _rm_path,
        )
        if _rm_spec is None or _rm_spec.loader is None:
            raise ImportError(f"archive_lib: cannot resolve role_map at {_rm_path}")
        _role_map = _ilu.module_from_spec(_rm_spec)
        sys.modules[_rm_spec.name] = _role_map
        _rm_spec.loader.exec_module(_role_map)
    return _role_map


def is_qpb_managed_agents_md(path: Path) -> bool:
    """True when ``path`` is a file carrying the QPB sentinel prefix on
    one of its first 5 non-empty lines (i.e. QPB generated it)."""
    path = Path(path)
    if not path.is_file():
        return False
    head_lines = [ln for ln in _read_text(path).splitlines() if ln.strip()][:5]
    return any(QPB_AGENTS_SENTINEL_PREFIX in ln for ln in head_lines)


def safe_write_agents_md(target_path: Path, content: str) -> str:
    """Write AGENTS.md at ``target_path`` while respecting
    operator-authored content.

    Returns one of:
      - ``"wrote"``        — no prior file; created fresh.
      - ``"regenerated"``  — existing file carried the
                             ``QPB_AGENTS_SENTINEL_PREFIX`` on one of
                             the first 5 non-empty lines (any QPB
                             version); refreshed in place with the
                             current version's full sentinel.
      - ``"preserved"``    — existing file lacked the QPB prefix
                             (operator-authored); left untouched and
                             a WARN line was emitted.

    v1.5.4 Phase 3.6.5 (B-17, H5 fix): the sentinel-on-first-lines
    discipline lets operators author their own AGENTS.md without
    losing it to a re-run. To opt back into QPB-managed
    regeneration, move the operator file aside (e.g. to
    ``AGENTS.qpb-preserved.md``) and re-run.

    v1.5.4 Phase 3.7 Fix 3 (Round 8 HIGH): detection matches on the
    ``QPB_AGENTS_SENTINEL_PREFIX`` rather than the literal v1.5.4
    string, so cross-version regeneration works (v1.5.5 detecting
    v1.5.4-generated files as QPB-managed; v1.5.4 detecting a
    hypothetical v1.5.5-generated file the same way).
    """
    target_path = Path(target_path)
    if target_path.is_file():
        if not is_qpb_managed_agents_md(target_path):
            print(
                f"WARN: AGENTS.md exists at {target_path} and appears "
                "operator-authored (no QPB sentinel in the first 5 "
                "non-empty lines). Preserving existing file. To opt "
                "into QPB-managed regeneration, move your AGENTS.md "
                "aside (e.g., AGENTS.qpb-preserved.md) and re-run.",
                file=sys.stderr,
            )
            return "preserved"
        outcome = "regenerated"
    else:
        outcome = "wrote"
    body = content if content.endswith("\n") else content + "\n"
    if not body.lstrip().startswith(QPB_AGENTS_SENTINEL_PREFIX):
        body = f"{QPB_AGENTS_SENTINEL}\n{body}"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(body, encoding="utf-8")
    return outcome


def extract_exploration_narrative(quality_dir: Path) -> str:
    """Pull the architecture / domain narrative excerpt from
    EXPLORATION.md. v1.5.4 Phase 3.6.5 (M9 fix): the AGENTS.md
    "What this is" section needs more than the role-map percentages
    — operators want the architectural framing the LLM produced.

    Heuristic: find the first heading-section whose title contains
    'architecture', 'domain', or 'stack' (case-insensitive); return
    up to 800 characters of body text. Fall back to the first
    non-empty paragraph if no such heading exists. Returns "" when
    EXPLORATION.md is absent.
    """
    path = quality_dir / "EXPLORATION.md"
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    import re as _re
    pat = _re.compile(
        r"^#+\s+([^\n]*(?:architect|domain|stack)[^\n]*)\n(.*?)(?=^#+\s|\Z)",
        _re.IGNORECASE | _re.MULTILINE | _re.DOTALL,
    )
    m = pat.search(text)
    if m:
        body = m.group(2).strip()
    else:
        # First non-empty paragraph after the title.
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        body = paragraphs[1] if len(paragraphs) > 1 else (paragraphs[0] if paragraphs else "")
    if len(body) > 800:
        body = body[:800].rsplit(" ", 1)[0] + " …"
    return body


def extract_deferred_bugs(quality_dir: Path) -> list:
    """Return BUG entries from BUGS.md whose disposition is
    'deferred', for inclusion in AGENTS.md's Caveats section.
    Each entry is (bug_id, title)."""
    path = quality_dir / "BUGS.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    import re as _re
    out: list = []
    headings = list(_re.finditer(
        r"^###\s+(BUG-[A-Za-z0-9]+)(?:\s*[:.\-]\s*(.+))?$",
        text,
        _re.MULTILINE,
    ))
    for i, match in enumerate(headings):
        bug_id = match.group(1)
        title = (match.group(2) or "").strip()
        # Section runs from this heading's end to the next BUG heading
        # (or EOF). Bounding the search per-bug prevents disposition
        # lines from a later bug bleeding into this one's match.
        section_start = match.end()
        section_end = (
            headings[i + 1].start() if i + 1 < len(headings) else len(text)
        )
        section = text[section_start:section_end]
        if _re.search(
            r"(?im)^\s*-?\s*\*?\*?\s*Disposition\*?\*?\s*[:\-]\s*deferred",
            section,
        ):
            out.append((bug_id, title or "(no title)"))
    return out


def generate_agents_md_content(repo_dir: Path) -> str:
    """Assemble the AGENTS.md body. Pulls role-map summary,
    EXPLORATION narrative, REQ/BUG counts, gate verdict, and deferred
    BUG list. v1.5.4 Phase 3.6.5 (B-17)."""
    repo_dir = Path(repo_dir)
    quality = repo_dir / "quality"
    role_map_lib = _load_role_map_module()
    role_map_data = role_map_lib.load_role_map(role_map_lib.default_path(repo_dir))
    summary = (
        role_map_lib.summarize_role_map(role_map_data)
        if role_map_data is not None
        else None
    )
    pcts = (summary or {}).get("percentages") or {}

    # Counts from INDEX (best-effort; INDEX may be the stub).
    index_path = quality / "INDEX.md"
    req_count = 0
    bug_count = 0
    gate_verdict = "unknown"
    if index_path.is_file():
        payload = load_index_payload(index_path)
        if isinstance(payload, dict):
            summary_block = payload.get("summary") or {}
            reqs = summary_block.get("requirements") or {}
            if isinstance(reqs, dict):
                req_count = sum(
                    int(v) for v in reqs.values() if isinstance(v, int)
                )
            bugs = summary_block.get("bugs") or {}
            if isinstance(bugs, dict):
                # Severity-only sum (matches RUN_INDEX convention).
                bug_count = sum(
                    int(bugs.get(s, 0))
                    for s in ("HIGH", "MEDIUM", "LOW")
                    if isinstance(bugs.get(s, 0), int)
                )
            gate_verdict = str(summary_block.get("gate_verdict") or "unknown")

    narrative = extract_exploration_narrative(quality)
    deferred = extract_deferred_bugs(quality)

    lines: list = []
    lines.append(f"{QPB_AGENTS_SENTINEL}")
    lines.append("")
    lines.append("# AGENTS.md")
    lines.append("")
    lines.append(
        "Per-project orientation for agents working on this repository "
        "after a Quality Playbook run."
    )
    lines.append("")
    lines.append("## What this is")
    lines.append("")
    if summary:
        lines.append(f"- Files in scope: **{summary.get('file_count', 0)}**")
        lines.append(
            f"- Surface mix: skill {pcts.get('skill_share', 0.0):.0%} / "
            f"code {pcts.get('code_share', 0.0):.0%} / "
            f"tool {pcts.get('tool_share', 0.0):.0%} / "
            f"other {pcts.get('other_share', 0.0):.0%}"
        )
        lines.append(f"- Role-map provenance: `{summary.get('provenance', 'unknown')}`")
    else:
        lines.append(
            "- (No role map present — Phase 1 has not yet produced "
            "`quality/exploration_role_map.json`.)"
        )
    lines.append(f"- Requirements derived: **{req_count}**")
    lines.append(f"- Bugs surfaced: **{bug_count}**")
    lines.append(f"- Gate verdict: **{gate_verdict}**")
    lines.append("")
    if narrative:
        lines.append("### Architecture / domain (excerpt from EXPLORATION.md)")
        lines.append("")
        lines.append(narrative)
        lines.append("")
    lines.append("## Read first")
    lines.append("")
    lines.append("- `quality/REQUIREMENTS.md` — derived behavioral requirements + use cases.")
    lines.append("- `quality/BUGS.md` — every defect surfaced this run, with disposition.")
    lines.append("- `quality/EXPLORATION.md` — the architectural framing Phase 1 produced.")
    lines.append("- `quality/INDEX.md` — run metadata (timestamps, gate verdict, role breakdown).")
    lines.append(
        "- `quality/exploration_role_map.json` — per-file role tagging "
        "that drives Phase 2 wiring."
    )
    lines.append("- `quality/writeups/BUG-<id>.md` — per-bug writeups.")
    lines.append("- `quality/patches/` — fix and regression-test patches.")
    lines.append("- `quality/code_reviews/`, `quality/spec_audits/`, `quality/results/`, `quality/control_prompts/`, `quality/mechanical/` — intermediate pipeline artifacts.")
    lines.append("- `quality/previous_runs/` — historical archives.")
    lines.append("")
    lines.append("## How to extend the review")
    lines.append("")
    # v1.5.4 Phase 3.7 Fix 4 (Round 8 HIGH): use the actual flag names
    # (positional `.` for the target; `--phase` singular). The earlier
    # template strings referenced --target / --phases which don't
    # exist; every v1.5.4 run produced an AGENTS.md whose extension
    # commands would fail with "unrecognized arguments".
    lines.append("- Re-run a single phase: `python -m bin.run_playbook . --phase <N>`.")
    lines.append(
        "- Run an iteration strategy: `python -m bin.run_playbook . "
        "--strategy <gap|unfiltered|parity|adversarial> --next-iteration`."
    )
    lines.append(
        "- Re-run the gate offline: "
        "`python3 .github/skills/quality_gate.py .` from the target root."
    )
    lines.append("")
    lines.append("## Caveats and known issues")
    lines.append("")
    if deferred:
        for bug_id, title in deferred:
            lines.append(f"- **{bug_id}** — {title} (disposition: deferred)")
    else:
        lines.append(
            "- No bugs were marked `disposition: deferred` in this run."
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI — compatibility-fork subcommands (dispatched by quality_playbook)
# ---------------------------------------------------------------------------


def finalize_index_main(argv: Optional[List[str]] = None) -> int:
    """`quality_playbook finalize-index [<repo>]` (CC-03)."""
    parser = argparse.ArgumentParser(
        prog="quality_playbook finalize-index",
        description=(
            "Map the last `RESULT: GATE …` line of "
            "quality/results/quality-gate.log into quality/INDEX.md "
            "summary.gate_verdict (PASSED→pass, PASSED WITH CLEANUP "
            "NEEDED→pass-with-cleanup, FAILED→fail) and stamp "
            "run_timestamp_end / duration_seconds. Run it after the "
            "Phase 6 gate and before spawning the auditor."
        ),
    )
    parser.add_argument("repo", nargs="?", default=".", help="Target repo root (default: .)")
    args = parser.parse_args(argv)
    try:
        result = finalize_index_gate_verdict(Path(args.repo))
    except ArchiveError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"gate_result: RESULT: GATE {result['result']}")
    print(f"gate_verdict: {result['gate_verdict']}")
    print(f"run_timestamp_end: {result['run_timestamp_end']}")
    print(f"duration_seconds: {result['duration_seconds']}")
    return 0


def agents_md_main(argv: Optional[List[str]] = None) -> int:
    """`quality_playbook agents-md [<repo>]` (CC-15)."""
    parser = argparse.ArgumentParser(
        prog="quality_playbook agents-md",
        description=(
            "Write or regenerate the QPB-managed AGENTS.md at the target "
            "repo root from the quality/ artifacts. An operator-authored "
            "AGENTS.md (no QPB sentinel in its first 5 non-empty lines) "
            "is preserved untouched."
        ),
    )
    parser.add_argument("repo", nargs="?", default=".", help="Target repo root (default: .)")
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    target = repo / "AGENTS.md"
    outcome = safe_write_agents_md(target, generate_agents_md_content(repo))
    print(f"AGENTS.md {outcome}: {target}")
    return 0


# ---------------------------------------------------------------------------
# CLI — operator-driven archive for failed / partial runs
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    # v1.5.7 089x: no-args is purpose-banner-safe.
    _argv_list_089x = list(sys.argv[1:] if argv is None else argv)
    try:
        from bin._purpose import print_command_intro as _print_command_intro
        from bin._purpose import print_help_banner as _print_help_banner
    except ImportError:
        from _purpose import print_command_intro as _print_command_intro  # type: ignore[no-redef]
        from _purpose import print_help_banner as _print_help_banner  # type: ignore[no-redef]
    if not _argv_list_089x:
        _print_command_intro(
            name='archive_lib',
            summary=(
            "QPB run-archive helpers — snapshot quality/ between "
            "runs + restore from a snapshot. "
            ),
            role=(
            "Imported by run_playbook.py to archive each iteration's "
            "quality/ outputs into quality/previous_runs/. Has a CLI "
            "for operator-side snapshot management. "
            ),
            usage_hint='python3 -m bin.archive_lib --list <target>',
        )
        return 0

    # v1.5.7 090a: full attribution banner at top of --help.
    _print_help_banner(_argv_list_089x)

    parser = argparse.ArgumentParser(
        description=(
            "Archive the current quality/ tree to "
            "quality/previous_runs/<timestamp>[-FAILED]/ (v1.5.4 Phase 3.6.2 "
            "B-19; legacy quality/runs/ archives remain readable but new "
            "archives land under previous_runs/). "
            "Operator-driven; the orchestrator auto-invokes archive_run on a clean "
            "gate pass, so use this only to preserve a failed or partial run before "
            "the next run's overwrite."
        ),
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Target repository root (default: current working directory).",
    )
    parser.add_argument(
        "--status",
        choices=("success", "failed", "partial"),
        default="success",
        help="Archive status; determines folder suffix. success = no suffix.",
    )
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Override the archive timestamp (basic ISO 8601 YYYYMMDDTHHMMSSZ). "
        "Defaults to the current UTC time.",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    ts = args.timestamp or utc_compact_timestamp()
    try:
        archive = archive_run(repo, ts, status=args.status)
    except ArchiveError as exc:
        print(f"archive: {exc}", file=sys.stderr)
        return 1
    print(f"Archived quality/ to {archive.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
