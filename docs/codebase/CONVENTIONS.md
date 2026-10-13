# Coding Conventions

Evidence snapshot: 2026-10-13, HEAD `746bfeb`. Distinguish observed code patterns
from instructions explicitly required by the repository.

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule or observed pattern | Example | Evidence |
|------|--------------------------|---------|----------|
| Python files | Observed snake_case; regression files often include release/instruction suffixes | `doc_classification.py`, `test_render_contract_v160.py` | [classifier](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py), [tests](../../bin/tests/test_render_contract_v160.py) |
| Functions/methods | Observed snake_case; internal helpers often begin with `_` | `renumber_to_document_order`, `_remap_cross_refs` | [requirements helpers](../../plugins/quality-playbook/skills/quality-playbook/scripts/requirements_render.py) |
| Classes/protocols | Observed PascalCase, including dataclasses and typed protocols | `RunnerResult`, `LLMRunner`, `ProgressState` | [runners](../../bin/skill_derivation/runners.py), [protocol](../../bin/skill_derivation/protocol.py) |
| Constants/env vars | Observed uppercase underscore-separated names | `DEFAULT_COUNCIL_MEMBERS`, `QPB_CHANNEL` | [Council config](../../plugins/quality-playbook/skills/quality-playbook/scripts/council_config.py), [validator](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_validate.py) |
| JavaScript | Transport shim uses camelCase functions and uppercase constants | `probePython`, `translateArgv`, `PY_MIN_MINOR` | [npm shim](../../bin/quality-playbook.js) |
| Operational artifacts | Uppercase Markdown names, lowercase JSON/JSONL names | `REQUIREMENTS.md`, `requirements_manifest.json` | [schemas](../../schemas.md), [skill](../../SKILL.md) |

Naming observations cover installer, runner, resolver, builder, classifier,
ingest, gate, state, config, heartbeat, persona, derivation, and test files rather
than generated output.

### 2) Formatting and Linting

- Python examples use four-space indentation, docstrings, annotations, and
  frequently `from __future__ import annotations`.
- The [npm shim](../../bin/quality-playbook.js) uses `"use strict"` and
  two-space JavaScript indentation.
- No root formatter/linter configuration or lint command was found by the
  scan/config search. `noqa`, `type: ignore`, and coverage pragmas occur, but
  their presence alone does not establish an enforced linter.
- [TODO] No repository-wide static type-check command or enforcement policy was
  found. This is not a TypeScript application; no TS strictness setting was found.
- Code and artifacts commonly use explicit UTF-8 reads/writes; subprocess text
  handling in [run_prompt](../../bin/run_playbook.py) specifies UTF-8 and
  replacement behavior for platform compatibility.
- Run commands: use existing tests (see [TESTING.md](./TESTING.md)); [TODO] lint
  and format commands are unspecified rather than invented here.

### 3) Import and Module Conventions

- Observed grouping is future imports, standard library, then project imports,
  with some deliberate late/path-loaded imports.
- [bin/__init__.py](../../bin/__init__.py) extends the package search path to the
  plugin's scripts. Consumers still write `from bin import ...`.
- Entry scripts frequently bootstrap repository/install paths on `sys.path`.
  Some bundled modules support both package-relative and flat-script imports.
  See [quality_playbook.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_playbook.py).
- The [clone installer](../../bin/install_skill.py) loads the hyphenated plugin
  location using `importlib` and re-exports implementation names.
- The [published CLI](../../quality_playbook_cli/__init__.py) registers privately
  loaded modules in `sys.modules` before execution, supporting dataclass/type
  resolution without publishing a top-level `bin` package.
- [TODO] No universal import sorter or public-export policy is configured.
  The CLI has an explicit `__all__`; the installer shim deliberately re-exports
  private helpers for compatibility.

### 4) Error and Logging Conventions

- Pure helper layers commonly raise named exceptions: `IngestError`,
  `IsolationError`, `CopilotCLIUnavailable`, and `UpstreamIncompleteError`.
  [run_state_lib.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py)
  returns or raises without a logging integration.
- The [installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py)
  emits structured `event=<name>` lines and exit codes, with optional prose.
  Usage refusal is 64; smoke/downgrade failure is 65.
- [RunnerResult](../../bin/skill_derivation/runners.py) captures stdout, stderr,
  elapsed milliseconds, and return code. Adapter timeouts become code 124.
  A missing batch-runner command is written as an error and returns 127.
- The [runner](../../bin/run_playbook.py) logs exact invocations, full prompts,
  combined transcripts, and child exit codes. Gate messages have stable,
  consumer-parsed verdict strings.
- These patterns are not uniform fail-fast guarantees: Council config warns and
  falls back on malformed roster data, and CLI version detection has an unknown
  fallback. See [Council config](../../plugins/quality-playbook/skills/quality-playbook/scripts/council_config.py)
  and [CLI](../../quality_playbook_cli/__init__.py).
- Privacy boundaries: [.gitignore](../../.gitignore) excludes gathered/private
  intake material and local installations; persona staging restricts inputs.
  [TODO] A general prompt/transcript redaction policy was not found in the
  inspected logging path.

### 5) Testing Conventions

- Tests primarily use `unittest.TestCase` in `bin/tests/test_*.py`. Assertions,
  temporary directories, injected streams, stubs, and `unittest.mock` support
  isolation. See [state tests](../../bin/tests/test_run_state_lib.py) and
  [classification tests](../../bin/tests/test_doc_classification_v160.py).
- Tests often name the historical defect, design section, or runner instruction.
  [Render-contract tests](../../bin/tests/test_render_contract_v160.py) pair clean
  fixtures with deliberate bad mutations and an AUDIT table.
- [DEVELOPMENT_PROCESS.md](../../ai_context/DEVELOPMENT_PROCESS.md) requires
  mutation-bite evidence and invariant tables for relevant regression classes.
  These are process requirements, not evidence that every test has been bitten.
- [TODO] No enforced numerical line-coverage threshold was found. Benchmark
  process compliance and bug recall are separate quality signals.
- The local pytest shim rejects node IDs and does not implement external pytest's
  general selector/plugin interface.

### 6) Evidence

- [bin/skill_derivation/runners.py](../../bin/skill_derivation/runners.py)
- [bin/skill_derivation/protocol.py](../../bin/skill_derivation/protocol.py)
- [bin/run_playbook.py](../../bin/run_playbook.py)
- [canonical installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py)
- [quality_playbook_cli/__init__.py](../../quality_playbook_cli/__init__.py)
- [pytest/__main__.py](../../pytest/__main__.py)
- [ai_context/DEVELOPMENT_PROCESS.md](../../ai_context/DEVELOPMENT_PROCESS.md)
- [.gitignore](../../.gitignore)
