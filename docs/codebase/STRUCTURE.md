# Codebase Structure

Evidence snapshot: 2026-10-13, HEAD `746bfeb`. Paths below distinguish editable
source, install-time bundle layout, and generated local artifacts.

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| Root skill and reference documents | Canonical main skill, artifact schemas, and phase-specific instructions | [SKILL.md](../../SKILL.md), [schemas.md](../../schemas.md), [requirements pipeline](../../references/requirements_pipeline.md) |
| `plugins/quality-playbook/` | Marketplace plugin: phase prompts, automation agents, installer/runtime scripts; its skill and reference links point back to root sources | [plugin manifest](../../plugins/quality-playbook/.claude-plugin/plugin.json), [bundle resolver](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py) |
| `plugins/quality-playbook-harness/` | Separately versioned orchestration skill and harness contracts | [harness skill](../../plugins/quality-playbook-harness/skills/quality-playbook-harness/SKILL.md) |
| `bin/` | Repository runner, distribution tooling, harness utilities, classifier debug utility, derivation package, and tests | [package bridge](../../bin/__init__.py), [runner](../../bin/run_playbook.py), [tick engine](../../bin/qpb_harness_tick.py) |
| `quality_playbook_cli/` | Published Python entry-point package; `_bundle/` is staged package data, not committed source | [CLI](../../quality_playbook_cli/__init__.py), [packaging constraint](../../pyproject.toml) |
| `pytest/` | Local compatibility shim over unittest | [runner](../../pytest/__main__.py) |
| `ai_context/` | User toolkit plus maintainer development, benchmark, and release-process context | [TOOLKIT.md](../../ai_context/TOOLKIT.md), [DEVELOPMENT_PROCESS.md](../../ai_context/DEVELOPMENT_PROCESS.md) |
| `docs/` | Versioned designs/plans, process evidence, historical bootstrap material, and this mapping | [v1.6.0 design](../design/QPB_v1.6.0_Design.md), [plan](../design/QPB_v1.6.0_Implementation_Plan.md) |
| `harness_plans/` | Checked-in benchmark/job plans, including platform-specific plans | [Windows plan](../../harness_plans/ship_readiness_windows_plan.json), [example config](../../harness_plans/config.example.json) |
| `runner/quality-playbook/` | Committed development-worker instruction/output record; live coordination files are excluded | [runner README](../../runner/quality-playbook/README.md), [ignore rules](../../.gitignore) |
| `metrics/`, `evidence/` | Benchmark measurement records and upstream bug/reproduction evidence | [metrics README](../../metrics/README.md), [evidence README](../../evidence/README.md) |
| `scripts/`, `repos/` | Blind-benchmark helpers and repo setup scripts; local benchmark trees/corpora under `repos/` are ignored | [blind gate](../../scripts/blind_benchmark_gate1.py), [setup script](../../repos/setup_repos.sh), [ignore rules](../../.gitignore) |
| `reference_docs/`, `quality/`, `reviews/` | Intake scaffold, generated audit outputs, and local review artifacts; tracking exceptions are explicit | [.gitignore](../../.gitignore) |
| `.claude-plugin/`, `.github/` | Marketplace catalog and tracked release workflow; local `.github` installations are ignored | [catalog](../../.claude-plugin/marketplace.json), [workflow](../../.github/workflows/publish.yml) |
| `images/` | README illustration assets | [README](../../README.md) |

The initial scanner omits directories named `bin`, so its tree and language
totals do not describe the repository's full source. A supplemental `git ls-files`
inventory covered `bin`, plugin scripts, CLI, local pytest, and the root backend:
259 tracked Python files, including 190 under test/fixture paths and 69 outside
test paths. There are 175 immediate `bin/tests/test_*.py` files. This is an
inventory, not a test-case count.

### 2) Entry Points

- Agent-operated execution starts at root [SKILL.md](../../SKILL.md), with
  installed equivalents in target projects. Mode A is an inline agent walkthrough;
  the Python runner is not its replacement.
- Operator/batch execution: [bin/run_playbook.py](../../bin/run_playbook.py),
  canonically `python -m bin.run_playbook` with literal target-directory arguments.
- Clone install: [bin/install_skill.py](../../bin/install_skill.py) is a shim;
  it loads the plugin's canonical installer by path.
- pip: [quality_playbook_cli.main](../../quality_playbook_cli/__init__.py) is the
  console-script entry selected by [pyproject.toml](../../pyproject.toml).
- npm: [bin/quality-playbook.js](../../bin/quality-playbook.js) is selected by
  [package.json](../../package.json), detects Python, and delegates to the CLI.
- Derivation pipeline: [bin/skill_derivation/__main__.py](../../bin/skill_derivation/__main__.py).
- Harness: [bin/qpb_harness_tick.py](../../bin/qpb_harness_tick.py) advances disk
  state; [bin/harness_ticker.py](../../bin/harness_ticker.py) provides terminal cadence.
- Validation/gate: plugin
  [qpb_validate.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_validate.py),
  [validate_phase_artifacts.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/validate_phase_artifacts.py),
  and [quality_gate.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py).

### 3) Module Boundaries

These are observed or explicitly documented boundaries, not newly imposed rules.

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| npm transport | Python detection, argument translation, stdio/exit propagation | A second install-routing policy; [shim](../../bin/quality-playbook.js) explicitly excludes it |
| Published CLI | Install/validate dispatch and loading bundled package data | Top-level importable `bin` distribution; [manifest](../../pyproject.toml) explicitly forbids it |
| Plugin scripts | Adopter runtime closure and canonical install helpers | Repository-only publishing/benchmark orchestration; separate enumeration lives in [builder](../../bin/build_channel_package.py) |
| `bin/skill_derivation/` | Four passes, checkpointing, citation search, divergence detection, LLM adapters | Skipping upstream-complete checks; [CLI](../../bin/skill_derivation/__main__.py) enforces transitions |
| Main skill vs harness | Audit procedure vs multi-job orchestration | Agent-invented harness state; [harness skill](../../plugins/quality-playbook-harness/skills/quality-playbook-harness/SKILL.md) delegates state to the tick engine |

### 4) Naming and Organization Rules

- Python filenames are predominantly `snake_case`; `test_*.py` identifies tests.
  Examples include [run_playbook.py](../../bin/run_playbook.py),
  [doc_classification.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py),
  and [test_render_contract_v160.py](../../bin/tests/test_render_contract_v160.py).
- Plugin and skill directories use hyphenated product names. Root operational
  Markdown uses uppercase names; reference filenames are mostly lowercase
  underscore-separated names. Versioned designs encode `QPB_vX.Y.Z`.
- Organization is by execution/distribution responsibility and audit feature,
  not web layers or npm workspaces.
- [bin/__init__.py](../../bin/__init__.py) extends `__path__` to plugin scripts,
  preserving `bin.<module>` imports. Explicit path-loading bridges directories
  whose hyphenated names are not Python module identifiers.
- Source `scripts/` becomes install/bundle `bin/`; the installed gate sits at
  install-root `quality_gate.py`. The builder uses destination mappings rather
  than assuming source-relative paths are install paths.
- Three tracked symlinks connect main skill, references, and toolkit to root
  sources. Initially text placeholders in this Windows worktree, all three
  were restored as resolving symlinks on 2026-10-13. Bundle enumeration now
  succeeds; see [CONCERNS.md](./CONCERNS.md).

### 5) Evidence

- [README.md](../../README.md), repository structure section
- [bin/__init__.py](../../bin/__init__.py)
- [bin/install_skill.py](../../bin/install_skill.py)
- [canonical installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py)
- [bin/build_channel_package.py](../../bin/build_channel_package.py)
- [.gitignore](../../.gitignore)
- Terminal: `git ls-files`, `git ls-files -s`, root/module directory listings,
  and counts restricted to the tooling scopes named above.
