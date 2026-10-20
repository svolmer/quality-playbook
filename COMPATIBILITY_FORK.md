# Compatibility fork: `svolmer/quality-playbook` `compat/v1.6.0-maf`

This branch is a **compatibility fork** of `andrewstellman/quality-playbook`
originally at `400f66f` (v1.6.0), see "Branch history" below. It exists so that the QualityPlaybook.Agent host
(Microsoft Agent Framework + MCP) can run QPB without contradictions in the
upstream contract. The plan's fork rules apply: changes are minimal, tested
and documented; the methodology, prompts, schemas and validators are
preserved except where a contradiction forced a change; every change is
listed here against its contradiction ID.

The contradiction IDs (CC-xx) refer to the host repo's
`docs/m0/contract-contradictions.md`. The operator approved every
resolution below on 2026-10-14:

- **`v1.6.0-maf.1`** (`23a5067`): CC-03, CC-05, CC-15 and CC-16, each
  "recommendation A".
- **`v1.6.0-maf.2`** (one commit on `23a5067`): CC-10 (option A), CC-17
  (option B), CC-18 (prose only) and CC-19 (option A), plus the
  prose-only reconciliations CC-02, CC-04, CC-06, CC-07, CC-08, CC-09,
  CC-11, CC-12, CC-13, CC-14, CC-20 and CC-21. CC-01 was already
  resolved in maf.1 as part of CC-05. That closes all 21 entries.

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
- **Releases** are annotated tags: `v1.6.0-maf.1` (`23a5067`) and
  `v1.6.0-maf.2` (`1319df0`). **The tags are the release identity, and the
  hosts pin by commit.** After the rebase described below they mark the
  pre-rebase commits, which are no longer on the branch.

## Branch history (rebased onto `main`, 2026-10-20)

`compat/v1.6.0-maf` was first published at `1319df0`, on top of upstream
`400f66f`. It was then rebased onto this repository's `main` (`1001b38`), so
the **branch is no longer based on `400f66f`**. Nothing the skill runs changed:

- The rebased commits carry identical changes (the patch-ids match the
  originals): `3a17786` is `23a5067` (maf.1) and `b763889` is `1319df0` (maf.2).
- Every runtime path (`bin/`, `plugins/`, `references/`, `schemas.md`,
  `SKILL.md`, `ai_context/`, `AGENTS.md`, `pyproject.toml`) is byte-identical to
  `1319df0`. `main` has not changed the skill since v1.6.0.
- The branch tree additionally carries what `main` adds on top of `400f66f`:
  `evidence/`, `runner/`, `docs/codebase/`, the migration plan under
  `docs/design/`, a changed `README.md` and `.github/workflows/publish.yml`, and
  without the virtio files under `repos/docs_gathered/`. A payload built from the
  branch is therefore larger (1439 files, about 50 MB) than the one built from
  `1319df0` (1365 files, about 37 MB), and the two have different payload hashes.
- `v1.6.0-maf.1` and `v1.6.0-maf.2` are not ancestors of the branch. The host
  keeps pinning `1319df0`; it is reachable through the `v1.6.0-maf.2` tag.
- The migration plan is not part of this fork. It lives on `main`; the copy under
  `docs/design/` on this branch is `main`'s frozen first version.
- Future fork work (maf.3 and later) lands on this branch as new commits with a
  new tag, and a host moves to it by changing its pin deliberately.

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

## v1.6.0-maf.2

None of these changes relaxes a gate or validator check. The two code
changes in `quality_gate.py` (CC-17, CC-19) are stricter than upstream.

### CC-10: the Mode B archive carries the computed verdict

**Contradiction.** `_log_phase_completion` computed `verdict` as
`pass-with-cleanup` for a `GATE PASSED WITH CLEANUP NEEDED` run, but then
archived with `gate_verdict_override="pass"` because `_gate_pass` is true
for both. The archived INDEX overstated the result and disagreed with the
live INDEX.

**Resolution.** `archive_run(..., gate_verdict_override=verdict)`. One
argument; archiving is still gated on a pass.

### CC-17: recheck status values and State R counts

**Contradiction.** `references/recheck_mode.md` defines four statuses
(`FIXED`, `PARTIALLY_FIXED`, `STILL_OPEN`, `INCONCLUSIVE`) and four summary
keys. State R reported "K still OPEN" and dropped `PARTIALLY_FIXED`. The
gate checked only that `results` and `summary` existed.

**Resolution.**

- State R (`references/what_just_happened.md`) reports all four counts
  under the schema names and maps each placeholder to its summary key.
- `quality_gate.check_recheck_sidecar` calls the new
  `_check_recheck_statuses_and_summary`:
  - every `results[].status` must be one of the four values;
  - each of the four summary counts must be a non-negative integer equal
    to the per-status tally of `results`.
- Its stale "SKILL.md recheck template" comment now names
  `references/recheck_mode.md`.

### CC-18: config CLI names and Council-size claims (prose only)

- SKILL.md and AGENTS.md list the real `qpb_config` subcommands:
  `show|set-runner|set-roster|unset`.
- `references/runners_and_models.md` no longer claims a shipped Phase 6
  hard-fail at 1-of-3 / 0-of-3. It points to the `spec_audit.md`
  degradation rule (1-of-3 downgrades every finding to "Needs
  verification") and to the deferred resilience work. It also states that
  the code accepts any non-empty roster, so three distinct identifiers are
  the operator's (or host's) responsibility. No roster-size code check was
  added.

### CC-19: the gate fails an agent-validation line in the confirmation ledger

**Contradiction.** `schemas.md` §9.5 says a Feature H persona may never
append to `operator_confirmations.jsonl`. Only the writer
(`run_state_lib.append_confirmation`) enforced it; a line written around
the helper passed the gate.

**Resolution.** `check_operator_confirmations_append_only` emits a
substantive FAIL for any ledger line with
`source_type == "agent-validation"`.

**Residual risk (host-side).** A forged line that claims
`source_type: "operator-confirmation"` still passes both the helper and
the gate; a file cannot prove a human wrote it. The host plan's M4 adds a
host-side receipt for each confirmation actually collected, cross-checked
against the ledger.

### Prose-only reconciliations

- **CC-02:** the `run_playbook.py` docstring and comment list the
  four-value INDEX enum including `pass-with-cleanup` (the auditor and
  Phase 5 enumerations were fixed in maf.1).
- **CC-04:** the gate witness is re-specified everywhere it appears
  (`phase6.md`, `phase6_auditor.md`, `phase6_verify_guide.md`,
  `what_just_happened.md`) as the LAST `RESULT: GATE …` line plus the
  `Total:` line immediately preceding it, the anchor
  `run_playbook._read_gate_verdict_from_log` already uses. All three real
  `Total:` shapes are listed. The old "final two lines" wording is gone,
  because the gate prints a verdict block and a `::QPB::` sentinel after
  RESULT. PASS still requires `Total: 0 FAIL`.
- **CC-06:** `phase6_verify_guide.md` uses `^### BUG-` and cites
  `run_state_schema.md` row 6 for the `phase_end phase=6` cross-validation
  instead of restating it.
- **CC-07:** the steps of `phase6_verify_guide.md` that the auditor runs
  are read-only ("record as FAIL"). Fixing moves to a new "Fixes after a
  failing audit (executor only)" section: in Mode A the parent fixes,
  re-runs Part A0 and spawns a new auditor; in Mode B Phase 6 runs inline.
- **CC-08:** the `quality_gate.py` docstring documents all exit codes and
  says exit 1 is overloaded; consumers decide on the RESULT line.
- **CC-09:** SKILL.md defines `partial` as an aborted or incomplete run with
  no terminal gate verdict (a WARN-only run prints `GATE PASSED` → `pass`).
  The `"warn" in gate_result` branch in `run_playbook.py` is marked legacy.
- **CC-11:** `schemas.md` §11 says an absent `schema_version` is a legacy
  read path only (the validator FAILs non-`"2.0"` at Phase 5/6) and states
  the completion contract: gate RESULT `PASSED` or
  `PASSED WITH CLEANUP NEEDED`, AND
  `validate_phase_artifacts --phase 6` PASSED.
- **CC-12:** `schemas.md` §11 names the producers (Mode B runner; Mode A
  agent in Phase 5 plus the parent's `finalize-index` in Phase 6; never the
  gate) and points the shape reference to `phase_prompts/phase5.md`.
- **CC-13:** both `_index` tables in `run_state_schema.md` carry `"1.5.8"`
  (older files carry `"1.5.6"`); resume resolves the log path with
  `run_state_lib.resolve_run_state_path`.
- **CC-14:** `run_state_schema.md` row 2 lists `requirements_manifest.json`
  and `use_cases_manifest.json` and refers to the A-15 `--phase 2`
  validator for the full manifest contract.
- **CC-20:** `phase5.md` lists the conditional
  `summary.languages_detected` / `ran_on` / `untested_testable_languages`
  keys and their trigger rule.
- **CC-21:** SKILL.md and `what_just_happened.md` say fourteen states and a
  10-rule classifier; `phase6.md` defers end-of-baseline state selection to
  the classifier (S, then CN, then B).

## Host-side deltas (not in this fork; recorded for traceability)

- **CC-03:** the host applies the same RESULT-line mapping and the same
  mismatch-is-FAIL rule in its independent verifier.
- **CC-15:** the host returns the target's AGENTS.md to the operator as an
  adoption patch instead of writing it into the operator's working tree.
- **CC-16:** the host runs iterations natively, using the same prompt text
  as `run_playbook.iteration_prompt`, instead of shelling out to the runner.
- **CC-19:** the host keeps a receipt per collected operator confirmation
  and fails a run whose ledger has an `operator-confirmation` line with no
  matching receipt.

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
- maf.2 adds to the same file:
  - `ModeBPhase6ArchiveVerdictTests` (CC-10): the archive gets the same
    verdict as the live INDEX for a clean pass, a cleanup pass and a
    failing finalizer; a failed gate is not archived;
  - `RecheckSidecarStatusTests` (CC-17): a consistent sidecar and an
    empty recheck pass; an `OPEN` status and summary counts that are
    missing, negative, boolean or disagree with the tallies fail, as
    substantive FAILs;
  - `OperatorConfirmationsAgentValidationTests` (CC-19): an
    `agent-validation` ledger line is a substantive FAIL and the writer
    refuses the same record; a human line passes; a forged
    `operator-confirmation` line still passes (pinning the residual risk
    the host must close);
  - `WitnessShapeTests` (CC-04): the three documented witness shapes
    match `quality_gate._compute_final_verdict`, and every witness site
    lists them with no old shape or "final two lines" wording left;
  - `MafTwoProseContractTests`: pins for CC-06/07/08/09/11/12/13/14/17/
    18/20/21, and a check that no shipped `.md` file cites
    `schemas.md` (FINDING-50; `test_schemas_audit_191` checks this only
    when `_bundle/` is staged).
- `bin/tests/test_run_state_lib.py::test_validate_phase_artifacts_phase6_verify_contract`
  is extended for CC-05: INDEX.md missing, unparseable, and with a
  pending, null or unknown verdict all fail; the four final values pass.
- Updated pins (the intended prose changes, acknowledged in place):
  - `test_phase_prompts_externalized.EXPECTED_HASHES` for `phase5`
    (25874 → 26536 codepoints) and `phase6` (9151 → 12579);
  - `test_skill_md_self_encoding.SkillMdAgentsMdOwnershipTests`, whose
    phrases now name the `agents-md` generator. The test intent is kept:
    Phase 2 never writes AGENTS.md.
  - maf.2: `EXPECTED_HASHES` again for `phase5` (26536 → 27168,
    CC-20) and `phase6` (12579 → 13507, CC-04/CC-21).
  - maf.2: `test_phase6_gate_witness` searched for the old witness
    needle `Total: N FAIL, M WARN`, a shape the gate never prints. Its
    three needles now read `Total: 0 FAIL, M WARN`, the PASS shape the
    prose still requires. The test intent is kept.
- **Full suite compared with the upstream baseline at `400f66f`:**
  - maf.1: 3078 tests, 54 failures, 6 errors and 48 skipped;
  - maf.2: 3106 tests (28 added), 54 failures, 6 errors and 48 skipped;
  - baseline: 3055 tests, 54 failures, 5 errors and 47 skipped.
  - For both tags, every failure and error matches the baseline set
    except one, which is environmental:
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
