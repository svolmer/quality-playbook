# Codebase Concerns

Evidence snapshot: 2026-10-13, HEAD `746bfeb`. This mapping is not a full bug,
security, performance, or release audit. Observed failures, documented historical
limits, and unverified risks are distinguished below.

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| High | Some corpus acceptance tests depend on absent ignored trees | [corpus tests](../../bin/tests/test_doc_classification_v160.py), [.gitignore](../../.gitignore); both `repos/chi-t3/docs_gathered` and `repos/express-t3/docs_gathered` are absent | Sampled classification tests produce three failures and one error, not a clean-clone baseline | Restore intended private fixtures through the project's benchmark process or separately define an explicit missing-fixture policy |
| Medium | Orientation documents mix historical and current layout | [AGENTS.md](../../AGENTS.md), [DEVELOPMENT_CONTEXT.md](../../ai_context/DEVELOPMENT_CONTEXT.md), [classifier status](../../bin/classify_project.py), [README structure](../../README.md) | Agents/contributors can follow old paths or mistake a debug utility for live routing | Prefer root skill, current design, and inspected implementations; refresh stale orientation sections as a separate change |
| Medium | Release workflow does not run the Python test suite | Only tracked workflow is [publish.yml](../../.github/workflows/publish.yml); it stages, verifies versions, builds, and publishes | Passing workflow steps do not establish regression-suite health | [TODO] Confirm whether tests are enforced outside this workflow before proposing CI policy changes |
| Medium | Full prompts/transcripts are retained locally | [run_prompt](../../bin/run_playbook.py), [.gitignore](../../.gitignore) | Audited source/docs may be present in logs; ignoring files is not redaction | Review local artifact sharing/retention before moving logs; [TODO] global redaction policy is unknown |

Read-only reproduction of the clone-integrity problem:

```powershell
python -c "from pathlib import Path; from bin import install_skill; install_skill._bundle_files(Path.cwd())"
```

The observed `RuntimeError` names the mandatory bundle directory
`plugins\quality-playbook\skills\quality-playbook\references` as missing.
The path exists as a regular text file containing the symlink target, not as the
required directory. No clone repair or reinstall was performed.

The subsequent requested repair was blocked by Windows permissions:
`os.symlink` returned `WinError 1314`, the session was not elevated, and setting
`AllowDevelopmentWithoutDevLicense` under
`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock` was denied.
Developer Mode and Git configuration remained unchanged. The original
148-test baseline was rerun and reproduced the same six failures, one error,
and three skips; see [TESTING.md](./TESTING.md).

**Resolved on 2026-10-13:** standard UAC elevation successfully enabled Windows
Developer Mode. Repository-local `core.symlinks` is now `true`, and the three
tracked symlinks were restored after confirming each placeholder matched its
index content. All targets resolve; read-only bundle enumeration returns 69
files. No tracked source content changed and no reinstall was performed.
The repaired-checkout baseline ran 148 tests: 142 passed, three failures, one
error, two skips. All three prior symlink-related failures are gone; remaining
failures/errors require the absent chi/express corpus inputs.

### 2) Technical Debt

| Debt item | Why it exists / evidence | Where | Risk if ignored | Suggested fix |
|-----------|--------------------------|-------|-----------------|---------------|
| Duplicated exclusion/marker/bundle constants | Comments explain standalone gate/runtime constraints and explicitly request later consolidation | [gate](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py), [state](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py), [debug classifier](../../bin/classify_project.py) | Layout drift across installed and source surfaces | Preserve invariant pins; consolidate only through a standalone-safe shared surface |
| Coarse runner-success inference | TODO says first exit-code match and loose version/digit fallback lack per-runner/per-bug mapping | [gate](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py) | Ambiguous logs can leave TDD execution unproven | Follow the documented per-runner probe-hardening direction; do not infer success from text alone |
| Prose fixture checks are not live prose-drift detection | The current plan explicitly says golden renders cannot fail on a regression in prompt prose | [v1.6.0 plan](../design/QPB_v1.6.0_Implementation_Plan.md) | Mechanical tests can pass despite changed agent behavior | Retain live benchmark/readability evidence; [TODO] a calibrated drift baseline was not established here |

A tracked-source search of non-test `.py`, `.js`, and `.sh` under `bin`, `plugins`,
`quality_playbook_cli`, and `scripts` found **5 TODO/FIXME/HACK lines**:
one in the debug classifier, two in the gate, two in the state library.
This is a marker-line count, not five confirmed bugs. Test TODOs are coverage or
test-maintenance concerns, not counted as production debt. Bootstrap transcripts
were excluded rather than treated as live code.

### 3) Security Concerns

These are trust boundaries and verification gaps, not exploit findings.

| Risk | OWASP category | Evidence | Current mitigation | Gap |
|------|----------------|----------|--------------------|-----|
| Untrusted intake self-promotes to authoritative evidence | N/A: evidence-integrity boundary | [classifier](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py) | Content-validated contracts; hard-signal confirmation route; operator-authored decision channel; disclosed model-read authority | [TODO] Live provider/host behavior was not audited |
| Persona access beyond declared context | N/A: agent capability boundary | [persona orchestration](../../plugins/quality-playbook/skills/quality-playbook/scripts/persona_orchestration.py) | Isolated input staging and read-only, no-shell/no-network tool configuration | Module explicitly is not a kernel/network sandbox; [TODO] actual executor enforcement across hosts not exercised |
| Sensitive context in local logs/artifacts | N/A: local data-handling boundary | [runner](../../bin/run_playbook.py), [.gitignore](../../.gitignore) | Explicit ignored intake/local artifact paths and input isolation for personas | [TODO] No general redaction/retention guarantee established in reviewed logging path |
| Release credentials and publishing authority | N/A: supply-chain boundary | [publish workflow](../../.github/workflows/publish.yml), [publishers](../../bin/publish_pip.py) | OIDC workflow permissions and manual preflight/auth checks | [TODO] Remote trusted-publisher registration and approval policy not verified |

No exhaustive secret scan or vulnerability assessment was performed.

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|-------------|-----------------------|
| Large correctness-critical modules | Tracked line counts: gate 8,557; runner 6,487; state library 2,011; classifier 1,866 | Maintenance size is measured; runtime slowness is not | Larger cross-surface regression footprint | Use targeted invariant tests and bounded changes; do not assume size alone requires a rewrite |
| External AI calls dominate orchestration latency | [adapters](../../bin/skill_derivation/runners.py), [pacing](../../bin/run_playbook.py), [tick defaults](../../bin/qpb_harness_tick.py) | Adapters default to 600-second call limits; batch prompt calls have no explicit timeout in the inspected function | Provider stalls/quota pressure can hold jobs and pool slots | Use existing pacing/pool controls; [TODO] benchmark actual latency and quota before tuning |
| Local transcripts/history can be large | Scan's largest files include multi-megabyte bootstrap/evidence transcripts | File sizes observed, not a live bottleneck | Naive whole-repository reads consume time/context and distort metrics | Restrict scans to tracked live source and bounded artifact sections |

The maintainer context records rate-limit and model-dependent TDD issues, but is
partly a historical v1.5.7 snapshot. This map does not treat its old provider
limits as verified current account behavior.

### 5) Fragile/High-Churn Areas

Churn counts are commits touching a path (not changed-line counts), using the
2026-07-15 through 2026-10-13 window at this HEAD.

| Area | Why fragile | Churn signal | Safe change strategy |
|------|-------------|--------------|----------------------|
| [doc_classification.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py) | Multiple evidence lanes, hard-signal routing, operator provenance | 38 touches | Pair ordinary and hostile classification cases; verify citation/disclosure behavior |
| [phase1_exploration_guide.md](../../references/phase1_exploration_guide.md) | Model-facing classification/exploration contract | 28 touches | Cross-check prose with lane mechanics and benchmark evidence; backup references before editing |
| [quality_gate.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py) | Shared verdict parsing and many artifact contracts | 26 touches | Test exact verdict strings/categories and failing mutations, including standalone installs |
| [QPB_v1.6.0_Design.md](../design/QPB_v1.6.0_Design.md) | Scope and acceptance source changed during release | 22 touches | Read decision record and companion plan before implementing |

Reproduce: `git log --since=2026-07-15 --until=2026-10-14 --format= --name-only`
with the four paths above, then count non-empty path lines. Other high-churn
paths in the initial scan include ingest (17), phase-2 guide (16), render-contract
tests (16), and requirements pipeline (15).

#### Intent vs. reality divergences

1. **Portable distribution vs this Windows source checkout:** manifests declare
   OS independence, but the initial disabled symlink checkout prevented source
   bundle enumeration. This local mismatch is now repaired; it was not evidence
   that a dereferenced published package fails.
2. **Documented historical classifier vs current routing:** root agent guidance
   describes the v1.5.3 Code/Skill/Hybrid classifier; the implementation labels
   it debug-only and states the run path uses AI-produced file role maps.
3. **Historical test instructions vs tracked tests:** maintainer context points
   at the old `.github/skills/quality_gate/tests` suite. Current tests include
   standalone gate imports in `bin/tests`; only the publish workflow is tracked
   under `.github`.
4. **README examples vs clean-checkout output:** README describes generated
   self-audit artifacts under `quality/`, but [.gitignore](../../.gitignore)
   excludes that output except audit exceptions; top-level example files were
   absent during inspection.
5. **Scanner vs actual source:** the skill scanner excludes every `bin`
   directory, reports no common entry points, and counts only 38 Python files.
   Supplementing with tracked files reveals the runner/test surface and 259
   Python tooling files in the stated scopes. Scanner totals are not a complete
   repository LOC inventory.
6. **Future roadmap vs implementation guidance:** the
   [v1.8.0 design](../design/QPB_v1.8.0_Design.md) explicitly declares itself
   stale. A higher filename version does not supersede the current v1.6.0
   design/plan or main skill version.

### 6) `[ASK USER]` Questions

No unresolved intent-dependent decision is needed for this descriptive mapping.
No policy change, supported-platform decision, CI mandate, or release action is
inferred. The later symlink repair was explicitly requested by the operator.
Unknown operational evidence is marked `[TODO]` above; other remediation
suggestions are not implemented requirements.

### 7) Evidence

- [canonical installer](../../plugins/quality-playbook/skills/quality-playbook/scripts/install_skill.py)
- [bin/tests/test_doc_classification_v160.py](../../bin/tests/test_doc_classification_v160.py)
- [bin/tests/test_run_state_lib.py](../../bin/tests/test_run_state_lib.py)
- [doc_classification.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py)
- [quality_gate.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py)
- [run_state_lib.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py)
- [ai_context/DEVELOPMENT_CONTEXT.md](../../ai_context/DEVELOPMENT_CONTEXT.md)
- [v1.6.0 implementation plan](../design/QPB_v1.6.0_Implementation_Plan.md)
- [.github/workflows/publish.yml](../../.github/workflows/publish.yml)
- Terminal: bundle enumeration error; `git config --get core.symlinks`;
  `git ls-files -s`; tracked-source marker/line counts; bounded churn history;
  sampled test result recorded in [TESTING.md](./TESTING.md).
