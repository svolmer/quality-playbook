# Compatibility fork: `svolmer/quality-playbook` `compat/v1.6.0-maf`

This branch is a **compatibility fork** of `andrewstellman/quality-playbook`
at `400f66f` (v1.6.0). It exists so that the QualityPlaybook.Agent host
(Microsoft Agent Framework + MCP) can run QPB without contradictions in the
upstream contract. The plan's fork rules apply: changes are minimal, tested
and documented; the methodology, prompts, schemas and validators are
preserved except where a contradiction forced a change; every change is
listed here against its contradiction ID.

The contradiction IDs (CC-xx) refer to the host repo's
`docs/m0/contract-contradictions.md`. All four resolutions below are
"recommendation A", as approved by the operator on 2026-10-14.

## Identity and version

- **Upstream base:** `400f66f` (`fix(publish): version-parity pre-flight
  handles the derived __init__ version`), SKILL.md `metadata.version: 1.6.0`.
- **The version stays `1.6.0`.** This deviates from the AGENTS.md "bump the
  version for every change" convention, for a reason: `quality_gate.py`
  reads the skill version from SKILL.md (`detect_skill_version`) and
  `check_version_stamps` compares every generated artifact's stamp with it.
  A fork suffix such as `1.6.0+maf.1` would change the stamps and break
  stamp-consistency checks. The fork identity is recorded here and in the
  host's `deps/quality-playbook.lock.json` (`compatibilityFork`) instead.

## CC-03: the receipted gate verdict is written into INDEX.md before the audit

**Contradiction.** Phase 5 writes `quality/INDEX.md` with
`summary.gate_verdict: "pending"`. `validate_phase_artifacts --phase 6`
requires a final verdict. But the Mode A Phase 6 auditor is read-only, and
no one was assigned to write the verdict.

**Resolution.**

- The parent (executor) finalizes and the auditor verifies; the auditor
  never repairs.
- New bundled subcommand: `python3 -m bin.quality_playbook finalize-index .`
  (`archive_lib.finalize_index_gate_verdict`). It reads the LAST
  `RESULT: GATE …` line of `quality/results/quality-gate.log` and maps it
  through the existing `_GATE_RESULT_TO_VERDICT`
  (`PASSED` → `pass`, `PASSED WITH CLEANUP NEEDED` → `pass-with-cleanup`,
  `FAILED` → `fail`).
- It rewrites only the fenced JSON block of INDEX.md: `summary.gate_verdict`,
  `run_timestamp_end` and `duration_seconds`.
- If there is no RESULT line, or the JSON block is missing or invalid, it
  raises and writes nothing. The verdict is never guessed.
- `phase_prompts/phase6.md` gains **Part A0 — pre-audit finalization**. The
  parent ensures AGENTS.md exists, runs the gate into the log, runs
  `finalize-index`, regenerates AGENTS.md and then spawns the auditor. If
  the auditor returns FAIL, the parent fixes the problem, re-runs A0 and
  spawns a NEW auditor.
- In the Mode B branch the subprocess must not edit `gate_verdict`. The
  orchestrator already writes the verdict it receipted itself
  (`_finalize_iteration` followed by `write_live_index_final`).
- `phase_prompts/phase6_auditor.md`:
  - The enum now includes `pass-with-cleanup`.
  - New **INDEX verdict cross-check**: the INDEX `gate_verdict` must equal
    the mapping of the RESULT line the auditor witnessed. A mismatch makes
    the verdict FAIL.
  - The return format gains an `INDEX gate_verdict:` line.
- The Phase 5 INDEX enum in `phase_prompts/phase5.md` and the wording in
  `references/phase6_verify_guide.md` are updated to match.

## CC-05: Phase 6 completion requires a final INDEX verdict

**Contradiction.** `references/run_state_schema.md` row 6 and the
`run_state_lib` Phase 6 branch treated Phase 6 as complete without INDEX.md.
A comment claimed INDEX.md "was never adopted", which contradicts the
shipped Phase 5/6 contract.

**Resolution.**

- `run_state_lib.validate_phase_artifacts(…, 6)` also requires that
  `quality/INDEX.md` exists, that its fenced JSON parses to an object, and
  that `summary.gate_verdict` is in `PHASE6_FINAL_GATE_VERDICTS`
  (`pass`, `pass-with-cleanup`, `partial`, `fail`; never `pending`).
- The stale comment is corrected.
- `run_state_schema.md` row 6 and resume rules 3 and 4 now state the same
  rule: a still-`pending` verdict means Phase 6 is incomplete.
- `run_end` is appended only after row 6 is re-verified.

## CC-15: AGENTS.md exists before the gate that requires it

**Contradiction.** The gate requires a root `AGENTS.md`. Upstream Mode B
wrote it only `if gate_passed`, which deadlocked a first run. Mode A had no
sanctioned writer at all: the generator lived in `bin/run_playbook.py`,
which is not in the install bundle, and SKILL.md forbade writes outside
`quality/`.

**Resolution.**

- The generator moves into the bundled `archive_lib`:
  `QPB_AGENTS_SENTINEL*`, `is_qpb_managed_agents_md`,
  `safe_write_agents_md`, `extract_exploration_narrative`,
  `extract_deferred_bugs` and `generate_agents_md_content`.
  `bin/run_playbook.py` keeps its historical private names as aliases.
- No new module is added, so the install bundle and the AGENTS.md `cp`
  blocks are unchanged.
- New bundled subcommand: `python3 -m bin.quality_playbook agents-md .`
- **Mode B** (`run_playbook._log_phase_completion`):
  - writes AGENTS.md at Phase 5 close;
  - writes it again before the Phase 6 gate (for a standalone `--phase 6`);
  - regenerates it after the verdict is written, whatever the verdict.
  - Archiving is still gated on a pass.
- **Mode A:**
  - `phase5.md` ends with the one sanctioned write via `agents-md`.
  - `phase6.md` Part A0 regenerates it after `finalize-index`.
  - SKILL.md's "do NOT modify any file outside `quality/`" rule names this
    single exception, which is allowed through that command only.
- An operator-authored AGENTS.md (no `<!-- generated by QPB` sentinel) is
  always preserved.
- `_finalize_iteration`'s source-edit guardrail excuses `AGENTS.md` only
  while it is QPB-managed. An agent edit to an operator-authored AGENTS.md is
  still a violation.
- `quality_gate.py` is unchanged.
- The timing prose is updated in SKILL.md, `references/artifact_contract.md`,
  `references/phase1_exploration_guide.md` and
  `references/phase2_generation_guide.md`. Phase 2 still must not write
  AGENTS.md.

## CC-16: the Mode A iteration handoff is explicit and per-strategy

**Contradiction.** The root AGENTS.md says a full Mode A run includes all
four iteration strategies. SKILL.md told the agent to suggest `--full-run`,
which the runner refuses from an agent context.

**Resolution (prose only).**

- SKILL.md (Mode A scope), `phase6.md` (new "Iteration handoff" section) and
  root AGENTS.md now say the same thing: one call to
  `python3 -m bin.run_playbook --next-iteration --strategy X <target>` per
  strategy.
- The calls run in the order gap → unfiltered → parity → adversarial, from
  the QPB clone, and never use `--full-run`.
- **Precondition:** the auditor witnessed `RESULT: GATE PASSED` or
  `RESULT: GATE PASSED WITH CLEANUP NEEDED`, AND
  `RESULT: VALIDATION PASSED (phase 6)`.
- `--next-iteration` was already carved out of the agent-context refusal
  guard, so no code change is needed.

## Host-side deltas (not in this fork; recorded for traceability)

- **CC-03:** the host applies the same RESULT-line mapping and the same
  mismatch-is-FAIL rule in its independent verifier.
- **CC-15:** the host returns the target's AGENTS.md to the operator as an
  adoption patch instead of writing it into the operator's working tree.
- **CC-16:** the host runs iterations natively, using the same prompt text
  as `run_playbook.iteration_prompt`, instead of shelling out to the runner.

## Tests

- `bin/tests/test_compat_fork_maf.py` (new) covers:
  - `finalize-index`: every token, last-line-wins, the no-RESULT and bad
    JSON paths with nothing written, prose preservation and Phase 6
    completion;
  - both CLI subcommands;
  - sentinel detection and the `run_playbook` aliases;
  - Mode B Phase 5 and Phase 6 ordering;
  - the finalizer exemption;
  - prose pins for CC-03, CC-15 and CC-16.
- `bin/tests/test_run_state_lib.py::test_validate_phase_artifacts_phase6_verify_contract`
  is extended for CC-05: INDEX.md missing, unparseable, and with a
  pending, null or unknown verdict all fail; the four final values pass.
- Updated pins (the intended prose changes, acknowledged in place):
  - `test_phase_prompts_externalized.EXPECTED_HASHES` for `phase5`
    (25874 → 26536 codepoints) and `phase6` (9151 → 12579);
  - `test_skill_md_self_encoding.SkillMdAgentsMdOwnershipTests`, whose
    phrases now name the `agents-md` generator. The test intent is kept:
    Phase 2 never writes AGENTS.md.
- **Full suite compared with the upstream baseline at `400f66f`:** 3078
  tests, 54 failures, 6 errors and 48 skipped, against the baseline's 3055
  tests, 54 failures, 5 errors and 47 skipped.
  - Every failure and error matches the baseline set except one, which is
    environmental:
    `test_run_playbook.RunnerThreeModeAccessibilityTests.test_script_mode_help_succeeds_from_anywhere`
    spawns bare `python3`, which on this Windows host is the Python
    install-manager alias, and that alias times out after 15 s.
  - `python.exe bin/run_playbook.py --help` itself exits 0 in about 0.2 s.

## Process deviations

- **No `.bak` copies** of the edited skill and reference files. Git history
  is the backup on this branch.
- **No benchmark-repo runs.** The AGENTS.md convention asks for two
  benchmark runs, but this phase of the migration forbids live AI-provider
  calls. Verification is the offline QPB suite compared with the recorded
  upstream baseline (host repo `docs/m0/baseline/`).
