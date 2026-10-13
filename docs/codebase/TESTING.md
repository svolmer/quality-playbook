# Testing Patterns

Evidence snapshot: 2026-10-13, HEAD `746bfeb`. Commands describe repository
tooling; the observed run below is a small baseline sample, not full validation.

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary framework: Python standard-library `unittest` (local interpreter
  3.14.3). The root `pytest` package is a local unittest wrapper, not external
  pytest with plugins/fixtures.
- Assertion/mocking tools: `unittest.TestCase`, injected callables/streams,
  `unittest.mock`, temporary directories, and subprocess probes.
- From repository root on Windows:

```powershell
# Entire bin/tests discovery (may require benchmark corpus/tool prerequisites).
python -m pytest bin\tests
python -m unittest discover -s bin\tests -p "test_*.py"

# File-scoped tests; supports multiple files in one invocation.
python -m pytest bin\tests\test_run_state_lib.py bin\tests\test_doc_classification_v160.py

# Expensive real package build/install tests, gated by their prerequisites.
python -m pytest bin\tests\test_channel_install_e2e_090b.py
```

No separate universal unit/integration/E2E runner is configured; choose relevant
files. [TODO] No supported coverage command or configured threshold was found.
The local shim rejects `file::node` IDs and ignores unknown flags rather than
implementing external pytest's general flag semantics. Do not rely on `-k`,
coverage flags, or external pytest plugins through this shim.

### 2) Test Layout

- Tests mainly live in `bin/tests/test_*.py`, with supporting helpers and nested
  `bin/tests/fixtures`. There are 175 immediate test files at this snapshot,
  not 175 test cases.
- Many filenames capture a release/instruction or regression class, e.g.
  [test_render_contract_v160.py](../../bin/tests/test_render_contract_v160.py) and
  [test_channel_install_e2e_090b.py](../../bin/tests/test_channel_install_e2e_090b.py).
- Setup is per test/class (`setUp`, `setUpClass`, temporary directories, injected
  fakes), not a discovered global external-pytest fixture layer.
- Tests import `bin` helpers or explicitly add the plugin script directory before
  importing standalone gate/classification modules.
- [DEVELOPMENT_CONTEXT.md](../../ai_context/DEVELOPMENT_CONTEXT.md) still
  documents a gate suite under `.github/skills/quality_gate/tests`. That tracked
  suite was not found in this checkout; do not treat the historical command as
  an available test surface.

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|-------|----------|----------------|-------|
| Unit | Yes, checked-in tests | Classifier decisions, state parsing, checkpointing, config, resolver | [classification tests](../../bin/tests/test_doc_classification_v160.py), [state tests](../../bin/tests/test_run_state_lib.py) |
| Artifact integration | Yes, checked-in tests | Gate checks across manifests and rendered Markdown, bundle/prose parity | [render tests](../../bin/tests/test_render_contract_v160.py), [bundle completeness](../../bin/tests/test_install_skill_bundle_completeness.py) |
| Package E2E | Yes, checked-in tests; not executed here | Stage/build wheel or tarball, temp install, CLI install/validate | [channel E2E](../../bin/tests/test_channel_install_e2e_090b.py); skips on missing build/venv/Node/npm tools |
| Live AI/benchmark | Documented and recorded separately; not executed here | Bug recall and process compliance on pinned target repositories | [benchmark protocol](../../ai_context/BENCHMARK_PROTOCOL.md), [harness skill](../../plugins/quality-playbook-harness/skills/quality-playbook-harness/SKILL.md) |

### 4) Mocking and Isolation Strategy

- Filesystem tests use `TemporaryDirectory`, fixture JSON/JSONL, and local
  Markdown rather than modifying a real audited target.
- Classification tests inject model decisions, including naive/hostile
  promotion stubs, to test deterministic citation constraints without AI calls.
- Resolver/runner tests can mock CLI availability and subprocesses.
  [Channel tests](../../bin/tests/test_channel_install_e2e_090b.py) deliberately
  exercise real built artifacts in temporary environments instead of relying
  only on enumeration parity.
- [Prerequisite helpers](../../bin/tests/_channel_test_helpers.py) probe the
  actual `python -m build` and venv interfaces before expensive tests.
- Isolation is not universal: some classification tests directly read ignored
  `repos/chi-t3/docs_gathered` and `repos/express-t3/docs_gathered`. Those paths
  are absent here, and corpus tests do not all skip when absent.
- Symlink-dependent tests read plugin paths literally; a Windows checkout with
  symlinks materialized as text breaks those file assertions.

### 5) Coverage and Quality Signals

- Coverage tool + threshold: [TODO] No configuration found.
- Current repository-wide coverage: [TODO] Not measured.
- Quality process: [DEVELOPMENT_PROCESS.md](../../ai_context/DEVELOPMENT_PROCESS.md)
  specifies AUDIT-table invariant tests and mutation-bite discipline.
  [README](../../README.md) separates process compliance from actual bug recall.
  A green mechanical suite is not, on its own, a live recall benchmark.

#### Observed baseline sample

Executed on 2026-10-13:

```powershell
python -m pytest bin\tests\test_run_state_lib.py bin\tests\test_doc_classification_v160.py
```

Result: **148 tests, 6 failures, 1 error, 3 skipped; exit 1** (8.805 seconds).

- Three state-test failures read text-placeholder `SKILL.md` or inaccessible
  plugin `references/run_state_schema.md` paths. Git reports symlink mode
  `120000` for the source links, while `core.symlinks=false` in this checkout.
- Three classification failures and one `KeyError: '01_API_Reference.md'`
  depend on the absent chi/express corpus directories. The tests enumerate
  those paths without obtaining the intended fixture input.
- The failed checks predate this documentation change. They were not repaired
  or hidden. No full-suite pass is claimed.
- [TODO] Re-run after corpus setup, and establish a full baseline separately.
  This mapping did not fetch corpora, install dependencies,
  invoke AI, or build/publish packages.

#### Requested symlink repair and baseline rerun

On 2026-10-13, the same command was rerun after checking Windows symlink
permissions. Result: **148 tests, 6 failures, 1 error, 3 skipped; exit 1**
(9.456 seconds). The seven failing/error test names match the original sample.

The symlink repair could not proceed: a temporary `os.symlink` probe failed with
`WinError 1314` (required privilege not held), the process was not elevated,
and the attempted Developer Mode registry write was denied. Developer Mode
remained disabled; `core.symlinks` remained `false`; all three tracked link
placeholders still matched their index contents. No source files were replaced.
The missing chi/express corpora also remained absent.

The initial permission blocker was subsequently resolved through standard UAC
elevation (exit 0). Windows Developer Mode is enabled, repository-local
`core.symlinks=true`, and all three tracked symlinks resolve to the intended root
sources. Read-only bundle enumeration succeeds with 69 files; tracked file
contents remain unchanged.

The original two-file baseline was rerun against that repaired checkout:
**148 tests, 142 passed, 3 failures, 1 error, 2 skipped; exit 1**
(7.323 seconds). All three formerly failing symlink-dependent state tests now
pass. The remaining three failures and one error are the same chi/express
corpus-dependent tests; those ignored fixture directories remain absent.
The two skips reference absent bootstrap evidence. No full-suite pass is claimed,
and no corpora were fetched or fabricated.

### 6) Evidence

- [pytest/__main__.py](../../pytest/__main__.py)
- [bin/tests/test_run_state_lib.py](../../bin/tests/test_run_state_lib.py)
- [bin/tests/test_doc_classification_v160.py](../../bin/tests/test_doc_classification_v160.py)
- [bin/tests/test_render_contract_v160.py](../../bin/tests/test_render_contract_v160.py)
- [bin/tests/test_channel_install_e2e_090b.py](../../bin/tests/test_channel_install_e2e_090b.py)
- [bin/tests/_channel_test_helpers.py](../../bin/tests/_channel_test_helpers.py)
- Terminal: sample command/result above, `Test-Path` for both corpus directories,
  `git config --get core.symlinks`, and `git ls-files -s`.
