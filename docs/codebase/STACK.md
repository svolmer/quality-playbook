# Technology Stack

Evidence snapshot: 2026-10-13, repository HEAD `746bfeb`. This describes the
checked-out source, not the contents or availability of published packages.

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary language | Python tooling plus Markdown agent instructions; JavaScript is the npm transport shim | [Python package](../../pyproject.toml), [skill](../../SKILL.md), [npm shim](../../bin/quality-playbook.js) |
| Python runtime | Minimum 3.10; local inspection used Python 3.14.3 | [requires-python](../../pyproject.toml); terminal `python --version` |
| Node runtime | Minimum 18 for the npm channel; local inspection reported v26.10.0 | [engines.node](../../package.json); terminal `node --version` |
| Package managers | pip/uvx/pipx and npm/npx are documented distribution routes, not two application workspaces | [README](../../README.md), [pip manifest](../../pyproject.toml), [npm manifest](../../package.json) |
| Module/build system | Python packages and PEP 517 custom backend over setuptools; npm prepack stages the same bundle | [backend](../../_qpb_build_backend.py), [build configuration](../../pyproject.toml), [prepack](../../package.json) |
| Version | Main skill and channel manifests say 1.6.0; harness skill independently says 1.5.9 | [main skill](../../SKILL.md), [harness skill](../../plugins/quality-playbook-harness/skills/quality-playbook-harness/SKILL.md) |

No web application framework, ORM, or application-server deployment is declared
in the two root manifests. The main product is an agent-executed skill with
supporting CLIs.

### 2) Production Frameworks and Dependencies

| Dependency | Version | Role in system | Evidence |
|------------|---------|----------------|----------|
| Python standard library | Python >=3.10 | Filesystem state, JSON/JSONL, parsing, subprocesses, dataclasses, CLI parsing | [state library](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py), [installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py) |
| Node built-ins | Node >=18 | `child_process`, `path`, and `fs` for locating Python and forwarding CLI arguments | [npm shim](../../bin/quality-playbook.js) |
| External AI CLIs | [TODO] Installed versions and account-specific model availability were not probed | Claude, Copilot, Codex, and Cursor execute prompts; they are external prerequisites, not pip/npm library dependencies | [runner adapters](../../bin/skill_derivation/runners.py), [Copilot resolver](../../bin/copilot_resolver.py) |

The root Python project declares no runtime `dependencies` or optional extras.
The npm manifest declares neither `dependencies` nor `devDependencies`.
An import inventory of tracked non-test tooling found optional matplotlib,
numpy, and twine imports; these are separated below rather than attributed to
the core runtime.

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| setuptools >=68 | Isolated pip builds; the custom backend stages source before build delegation | [manifest](../../pyproject.toml), [backend](../../_qpb_build_backend.py) |
| `build`, pip, venv | Build and execute real channel artifacts in temporary environments | [channel tests](../../bin/tests/test_channel_install_e2e_090b.py), [prerequisite probes](../../bin/tests/_channel_test_helpers.py) |
| unittest; local `pytest` shim | Tests without an external pytest dependency | [shim](../../pytest/__main__.py), [representative tests](../../bin/tests/test_run_state_lib.py) |
| Git, gh | Repository operations, history, publish/submission checks | [submission script](../../bin/submit_awesome_copilot.py), [project classifier](../../bin/classify_project.py) |
| Twine | Operator-driven PyPI/TestPyPI uploads; [TODO] no version pin found in the root manifest | [pip publisher](../../bin/publish_pip.py) |
| matplotlib, numpy; optional `mmdc` | Manual calibration visualizations, not normal playbook execution; [TODO] versions are not pinned in the root manifest | [visualization utility](../../bin/visualize_calibration.py) |
| GitHub Actions | Release-triggered staging and publishing; Python 3.12 and Node 20 for staging, Node 22 for npm publishing | [workflow](../../.github/workflows/publish.yml) |

No root formatter/linter configuration or lint script was found by the scan and
config-file search. No container configuration was found in that search.
These observations do not establish the absence of private developer tooling.

### 4) Key Commands

From the repository root, using Windows shell paths:

```powershell
# Clone-based install into a separate target; requires intact source symlinks.
python -m bin.install_skill --into "C:\path\to\target" --ai-tool copilot

# Build tools are needed for package development, not core skill execution.
python -m bin.build_channel_package --stage
python -m build
npm pack

# Repository test runner; the local pytest package delegates to unittest.
python -m pytest bin\tests
python -m unittest discover -s bin\tests -p "test_*.py"
```

[TODO] No established lint/type-check command was found. Do not substitute
external pytest options for the local shim's supported interface. Staging stamps
version surfaces and writes an ignored bundle; it is not a read-only probe.
The initial symlink checkout blocker was repaired on 2026-10-13; read-only
bundle enumeration now succeeds with 69 files. Actual package builds and
installs were not exercised in that repair; see [CONCERNS.md](./CONCERNS.md).

### 5) Environment and Config

- Version source: metadata in root [SKILL.md](../../SKILL.md). Runtime version
  readers and build-time stamping are implemented by
  [_purpose.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/_purpose.py)
  and [build_channel_package.py](../../bin/build_channel_package.py).
- Operator configuration: `XDG_CONFIG_HOME` selects `qpb/config.json`; otherwise
  the fallback is the user's `.qpb/config.json`. Config supports runner and
  Council choices; [qpb_config.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_config.py)
  owns persistence.
- `QPB_MODEL` supplies the benchmark default model; `QPB_CHANNEL` distinguishes
  clone/pip/npm remediation. See
  [benchmark_lib.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/benchmark_lib.py)
  and [qpb_validate.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_validate.py).
- Worker telemetry uses `QPB_HEARTBEAT_PATH`, `QPB_TASK_ID`, and `QPB_RUN_STATE`;
  explicit flags can supply the corresponding values. See
  [qpb_heartbeat.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_heartbeat.py).
- No root `.env.example`/`.env.template` was found. AI CLI authentication and
  current model availability must be supplied by the operator's external tools;
  [TODO] neither was tested during mapping.
- This Windows worktree initially had `core.symlinks=false` and text placeholders
  for tracked symlinks. On 2026-10-13, standard UAC elevation enabled Windows
  Developer Mode, repository-local `core.symlinks` was set to `true`, and all
  three tracked links were materialized and verified. No global Git setting
  was changed.

### 6) Evidence

- [pyproject.toml](../../pyproject.toml)
- [package.json](../../package.json)
- [_qpb_build_backend.py](../../_qpb_build_backend.py)
- [publish.yml](../../.github/workflows/publish.yml)
- [bin/quality-playbook.js](../../bin/quality-playbook.js)
- [pytest/__main__.py](../../pytest/__main__.py)
- [bin/visualize_calibration.py](../../bin/visualize_calibration.py)
- Terminal: `python --version`, `node --version`, `git config --get core.symlinks`;
  AST import inventory over tracked non-test Python tooling.
