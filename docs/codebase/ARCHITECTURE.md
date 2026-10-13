# Architecture

Evidence snapshot: 2026-10-13, HEAD `746bfeb`. This is a map of execution and
artifact boundaries, not a claim that the Python code alone implements every
agent instruction.

## Core Sections (Required)

### 1) Architectural Style

- Primary style: an artifact-driven agent workflow with Python CLI support and
  disk-backed state machines. The [main skill](../../SKILL.md) specifies agent
  work; [state helpers](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py)
  and [the harness tick engine](../../bin/qpb_harness_tick.py) own mechanical state.
- Functional responsibilities are split into ingest/classification,
  requirements derivation, review/audit, reconciliation, and validation.
  The repository does not show controller/service/repository web layers.
- Constraints: installed runtime closure must be complete; evidence and
  citations must remain traceable; resumable work uses disk state rather than
  conversational memory. See [installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py)
  and [pass protocol](../../bin/skill_derivation/protocol.py).
- Interactive Mode A and operator-driven Mode B are distinct surfaces.
  [AGENTS.md](../../AGENTS.md) prohibits handing an interactive run to the batch
  runner; [run_playbook.py](../../bin/run_playbook.py) has agent-context guards.

### 2) System Flow

```text
Agent SKILL.md or operator runner
  -> installed closure validation
  -> reference documents + source exploration
  -> classification/role/requirements manifests + agent-authored artifacts
  -> code review + independent spec audit + TDD reconciliation
  -> phase validators + three-state gate
  -> quality artifacts, logs, and operator presentation
```

1. Entry selection determines who executes prompts: an interactive agent follows
   [SKILL.md](../../SKILL.md); an operator's
   [runner](../../bin/run_playbook.py) builds phase prompts and invokes AI CLIs.
   Phase 0 validation checks installed files, scaffolding, and environment.
2. [reference_docs_ingest.ingest](../../plugins/quality-playbook/skills/quality-playbook/scripts/reference_docs_ingest.py)
   reads `reference_docs`, obtains classification decisions, and writes
   `quality/formal_docs_manifest.json`. The
   [classifier](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py)
   evaluates three citation lanes: content-validated contracts, model-read
   authority with disclosure, and operator-confirmation-required material.
3. Agents produce exploration, a file role map, requirements, tests, and
   protocols. Skill-prose derivation has four gated passes in
   [skill_derivation](../../bin/skill_derivation/__main__.py).
   [requirements_render.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/requirements_render.py)
   groups and renumbers manifest records; it is not a complete prose renderer.
4. Review/audit and reconciliation are specified in the
   [skill](../../SKILL.md) and phase prompts. The
   [runner's run_prompt](../../bin/run_playbook.py) writes prompts and combined
   stdout/stderr transcripts around external CLI calls, then records exit status.
5. [run_state_lib.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py)
   records/validates JSONL phase state;
   [quality_gate.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py)
   checks artifacts. Gate outcomes are passed (exit 0), passed with cleanup
   needed (exit 0), or substantive failure (exit 1).
6. Results persist under the target's `quality/`; logs use per-run subtrees.
   [archive_lib.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/archive_lib.py)
   and [quality_playbook.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_playbook.py)
   provide archive/management operations.

A separate, deterministic installation path is:

```text
npm JS transport / pip CLI / clone installer shim
  -> canonical install()
  -> resolve target and source layout
  -> mapped bundle copy, operator-backup handling, scaffolding
  -> smoke checks + event=<name> output + exit code
```

Source resolution and bundle enumeration are in the
[canonical installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py).
The clone shim uses `importlib`; the packaged CLI loads `_bundle/bin` privately,
so published package data does not become an importable top-level `bin` package.

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| Skill/reference prose | Agent procedure, evidence rules, interviews, presentation | Fabricating a mechanical gate outcome | [SKILL.md](../../SKILL.md), [AGENTS.md](../../AGENTS.md) |
| Ingest/classification | File intake, citation-lane decisions, provenance disclosure | Treating extension/name or self-declared authority as sufficient citation proof | [classifier](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py) |
| Derivation protocol | Atomic checkpoints, JSONL receipts, upstream status checks | Advancing a cursor before durable output | [protocol](../../bin/skill_derivation/protocol.py) |
| Persona validation | Staged inputs, restricted-tool configuration, grounding/merge/apply/revert | Writing human operator confirmations on a persona's behalf | [orchestration](../../plugins/quality-playbook/skills/quality-playbook/scripts/persona_orchestration.py), [apply](../../plugins/quality-playbook/skills/quality-playbook/scripts/persona_apply.py) |
| Gate/state validators | Artifact contracts and explicit verdict categories | Counting audit-record gaps as substantive defects | [gate](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py) |
| Harness tick engine | Pool-slot state, dispatch envelopes, heartbeat interpretation, STOP handling | Making the agent reconstruct state from chat | [tick engine](../../bin/qpb_harness_tick.py) |

### 4) Reused Patterns

| Pattern | Where found | Evidence-backed purpose |
|---------|-------------|------------------------|
| Adapter/protocol | [LLMRunner and adapters](../../bin/skill_derivation/runners.py) | Common result shape across four external CLIs |
| Checkpoint and write-ahead ordering | [protocol.py](../../bin/skill_derivation/protocol.py) | JSONL receipt precedes cursor advancement; resume reconciles state |
| Atomic file replacement | [qpb_config.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_config.py), [run_state_lib.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py) | Avoid partial config/progress files |
| Idempotent state-machine tick | [qpb_harness_tick.py](../../bin/qpb_harness_tick.py) | Repeated ticks preserve transition semantics; STOP is read-only |
| Small transport/delegation shims | [npm shim](../../bin/quality-playbook.js), [clone shim](../../bin/install_skill.py), [pip CLI](../../quality_playbook_cli/__init__.py) | Share one installer instead of parallel routing implementations |
| Explicit executor seam | [persona_orchestration.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/persona_orchestration.py) | Test staging/tool restrictions independently of a live agent spawn |

The [progress monitor](../../bin/progress_monitor.py) uses a background thread
with event-driven shutdown and locks. The harness coordinates workers via
filesystem queue/results and heartbeat files, not a declared message broker.

### 5) Known Architectural Risks

- Source/install/package layouts differ and depend on symlink materialization.
  The initial Windows checkout failed bundle enumeration; restored symlinks now
  allow enumeration of 69 files. Future clones still require correct symlink
  handling; see [CONCERNS.md](./CONCERNS.md).
- Prose generation and live agent execution cannot be established by checking
  Python helpers alone. The [v1.6.0 plan](../design/QPB_v1.6.0_Implementation_Plan.md)
  explicitly says golden fixture checks are not a functional prose-drift detector.
- The gate and runner are large, high-churn modules. Shared standalone-runtime
  constants are deliberately duplicated and pinned by tests rather than
  consolidated universally.
- Persona staging/tool configuration is not a kernel or network sandbox.
  [TODO] Live executor enforcement across hosts was not exercised in this mapping.

### 6) Evidence

- [SKILL.md](../../SKILL.md)
- [bin/run_playbook.py](../../bin/run_playbook.py)
- [canonical installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py)
- [reference_docs_ingest.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/reference_docs_ingest.py)
- [doc_classification.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py)
- [run_state_lib.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py)
- [bin/skill_derivation/protocol.py](../../bin/skill_derivation/protocol.py)
- [bin/qpb_harness_tick.py](../../bin/qpb_harness_tick.py)
