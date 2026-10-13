# Quality Playbook: MAF/Copilot MCP Migration Implementation Plan

## 1. Purpose and status

**Planning handoff, not an implementation or a claim of runtime compatibility.**
The architectural decisions below were clarified with the operator. The proposed
implementation increments have explicit evidence and acceptance gates.

Build a separate Windows/.NET 10 application that exposes Quality Playbook
operations over local stdio MCP. Microsoft Agent Framework (MAF) owns the quality
workflow and its agents perform all AI reasoning through the GitHub Copilot SDK.
Consume the complete Python Quality Playbook (QPB) source tree as a pinned Git
dependency; preserve its methodology, prompts, deterministic utilities, schemas,
validators, generated artifacts, and Apache 2.0 attribution.

This is **not** a generic autonomous coding agent, a rewrite of QPB in C#, or an
MCP wrapper that delegates reasoning to the existing external-AI-CLI runner.
No .NET repository, projects, source dependency, or compatibility fork has been
created by this planning task.

## 2. Confirmed operator decisions

| Area | Confirmed decision |
|---|---|
| Repository topology | Separate .NET repository consuming a pinned QPB dependency. |
| First-release platform | Windows only; Visual Studio 2026 Copilot Chat; local stdio MCP. |
| Framework | .NET 10 LTS. |
| Preview packages | Permitted, with exact tested package versions pinned. |
| Dependency form | Pinned Git source dependency retaining the complete QPB core tree, not a piecemeal copy or package-only closure. |
| Initial dependency source | Official upstream v1.6.0 release ref, resolved and verified to an immutable commit during the baseline increment. |
| Compatibility changes | Minimal, tested, documented changes in a pinned QPB fork are permitted when necessary; preserve methodology, prompts, schemas, and validators. |
| Source isolation | Apply test/fix changes in an isolated Git worktree. Leave the original source untouched and return patches. |
| Dirty source | Require a clean source checkout before creating the audit worktree. |
| Job lifetime | Stop safely on stdio/client exit; support explicit resume after MCP host restart. No detached worker for the initial release. |
| Concurrency | One active quality job per host; never execute two jobs for the same target repository. |
| Durable state | SQLite host state plus separately persisted MAF checkpoint payloads; retain existing QPB JSONL logs. |
| Council roster | Explicit operator-supplied roster for every run; no host default. |
| Council independence | Three distinct resolved model IDs and separate, mutually blind contexts. Different vendors are not required. |
| Council unavailability | Block the Council stage. Changing the roster requires explicit operator approval before resume. |
| Human input | Pause with an awaiting-input status; Copilot Chat submits explicit operator answers through `qpb_resume`. |
| Commands | Operator-approved per-repository executable/argument allowlist, checked before every invocation. |
| Repository network access | Deny by host/tool policy by default; explicit run-scoped approval for restores, installation, or other network operations. Copilot provider connectivity is a separate required permission. |
| Trust scope | Trusted local repositories only. Child processes are not OS-sandboxed; disclose this limitation rather than claiming network/filesystem confinement. |
| Grouped verification | Accept requested phase groups, but always split Phase 6 into a fresh-context verifier and disclose the effective grouping. |
| Acceptance targets | One representative .NET repository and one non-.NET repository; select exact repositories and commits during the baseline increment. |
| Source-contract conflicts | Recheck against the pinned release; reconcile stale prose with its schemas and executable validators in a minimal compatibility fork before proceeding. |
| Plan location | Store this handoff in the current QPB checkout. Do not create or modify the future .NET repository during planning. |

### Inputs deliberately not invented here

The exact upstream/fork commit, NuGet versions, ordinary phase model assignments,
three Council model IDs, benchmark repositories/commits, approved commands,
execution budgets, state/worktree locations, retention policy, and distribution
format are not assigned speculative values. Resolve them at the indicated
increment or obtain explicit operator configuration before the relevant run.
An unavailable required input produces a visible configuration blocker.

## 3. Ground truth and feasibility evidence

### QPB sources

Use the pinned dependency's versions of these sources when implementing:

- [SKILL.md](../../SKILL.md): operational phase chain, artifact contracts,
  attribution, execution modes, and presentation.
- [v1.6.0 design](QPB_v1.6.0_Design.md): especially sections 5 and 6
  (coherence and human validation), section 8/F-2a (durable confirmations),
  section 8a's later three-lane classification revision, and section 8b
  (isolated persona remediation). Do not implement the superseded mechanical
  genre-floor design or import the deferred v1.6.1 precision scope by accident.
- [v1.6.0 implementation plan](QPB_v1.6.0_Implementation_Plan.md) and
  [development process](../../ai_context/DEVELOPMENT_PROCESS.md): source
  precedence, fixture acceptance, invariants, and truthful release evidence.
- [Existing runner](../../bin/run_playbook.py): phase selection, grouped
  contexts, full-run options, and iteration behavior. It is a behavioral
  reference, **not the new executor**.
- [Phase prompts](../../plugins/quality-playbook/skills/quality-playbook/phase_prompts/),
  [iteration reference](../../references/iteration.md),
  [recheck reference](../../references/recheck_mode.md),
  [artifact schemas](../../schemas.md), and
  [run-state schema](../../references/run_state_schema.md).
- [Derivation runners](../../bin/skill_derivation/runners.py),
  [derivation pass A](../../bin/skill_derivation/pass_a.py), and
  [prose-to-code divergence](../../bin/skill_derivation/divergence_prose_to_code_llm.py):
  replacing only the batch runner would leave nested AI CLI execution behind.
- [Document ingestion](../../plugins/quality-playbook/skills/quality-playbook/scripts/reference_docs_ingest.py),
  [persona orchestration](../../plugins/quality-playbook/skills/quality-playbook/scripts/persona_orchestration.py),
  and [Council semantic checks](../../plugins/quality-playbook/skills/quality-playbook/scripts/council_semantic_check.py):
  existing classifier, executor, and plan/assembly seams.
- [Install validator](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_validate.py),
  [phase validator](../../plugins/quality-playbook/skills/quality-playbook/scripts/validate_phase_artifacts.py),
  [quality gate](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py),
  and [fresh auditor prompt](../../plugins/quality-playbook/skills/quality-playbook/phase_prompts/phase6_auditor.md).

**Inspected checkout is not the approved dependency pin.** Its HEAD is
`746bfeb` ("Merge 1.6.1 into main ..."), while canonical skill metadata reads
`1.6.0`. Resolve the official release ref and revalidate all observations
against that immutable source before implementation.

**Known contract conflict:** the inspected run-state schema's Phase 6 table
says the INDEX artifact was never adopted, while the Phase 6 auditor and
executable phase validator require it. The validator also accepts
`pass-with-cleanup`, which is absent from one auditor enumeration. Recheck
these against the chosen release; reconcile the contradictory prose explicitly.
Do not silently choose a weaker completion contract.

The repaired local representative baseline was 148 tests: 142 passed, three
failed, one errored, and two skipped. Remaining failures require missing
chi/express corpora; this is neither a clean baseline nor a full-suite result.
See [test evidence](../codebase/TESTING.md). Establish migration baselines on
the approved source and selected acceptance targets.

### Official runtime documentation

- [GitHub: MAF/Copilot SDK integration](https://docs.github.com/en/copilot/how-tos/copilot-sdk/integrations/microsoft-agent-framework):
  documents wrapping a Copilot client as an `AIAgent` and currently shows a
  prerelease installation route.
- [Learn: GitHub Copilot agents](https://learn.microsoft.com/agent-framework/integrations/by-component/agent-services/github-copilot):
  documents .NET sessions, custom tools, permissions, and SDK-native approval.
  Custom `OnPreToolUse` hooks replace the integration's default approval hook;
  approval enforcement must therefore be tested, not assumed.
- [Learn: workflow checkpoints](https://learn.microsoft.com/agent-framework/workflows/checkpoints):
  documents checkpoints at completed supersteps and .NET checkpoint hooks.
  This does not establish exactly-once external side effects or durable
  Copilot-session recovery. Do not copy Python checkpoint APIs into C#.
- [Learn: build a C# MCP server](https://learn.microsoft.com/dotnet/ai/quickstarts/build-mcp-server):
  documents public stdio hosting and Copilot client configuration.
- [Learn: MCP tools with agents](https://learn.microsoft.com/agent-framework/agents/tools/local-mcp-tools):
  describes agents consuming MCP tools; it is not by itself a recipe for the
  application's public MCP server.

These sources establish feasibility candidates, not compatibility of a chosen
package set. No live provider authentication, model availability, or restart
experiment has been performed for this plan.

## 4. Proposed module structure and ownership

Use the requested four-project structure as the starting proposal, not a
generic agent platform or an extra project for each command:

```text
QualityPlaybook.Agent.sln
  src/
    QualityPlaybook.Mcp/
    QualityPlaybook.Orchestration/
    QualityPlaybook.AgentRuntime/
    QualityPlaybook.Core/
  tests/
    QualityPlaybook.Core.Tests/
    QualityPlaybook.Orchestration.Tests/
    QualityPlaybook.Mcp.Tests/
  external/
    quality-playbook/        complete Git dependency pinned to a commit
  docs/
    architecture.md
```

- **Mcp module:** transport, input validation, and thin operation handlers.
  No quality-review prompts, phase decisions, shell interface, or reasoning.
- **Orchestration module:** the small command interface, MAF workflow
  coordinator, phase/group dependencies, Council dispatch, validator-driven
  transitions, durable job state, artifact publication, and recovery.
- **AgentRuntime module:** Copilot-backed MAF agents and controlled execution
  tools, including the deterministic Python adapter. Its seams support live
  execution and test doubles; do not introduce interchangeable providers that
  the request does not need.
- **Core module:** typed run/options/results and application contracts. It is
  **not** a C# replacement for Python QPB's core.
- **Pinned Python dependency:** owns deterministic methodology contracts.
  Prefer a full Git submodule as the implementation of the chosen dependency
  form; record URL, commit, skill version, and content hashes. A compatibility
  fork changes the recorded pin and maintains an explicit change manifest.

Workflow scheduling and tool execution remain host-owned. The SDK owns its
documented internal tool-calling loop, operating only with the permissions and
tools the host authorizes. Agents cannot invoke the public lifecycle tools to
approve themselves or launch additional quality jobs.

The SDK may launch or connect to its documented Copilot CLI server transport.
That is distinct from launching `copilot -p`, `gh copilot --prompt`, Claude,
Codex, or Cursor as one-shot phase executors. Those legacy AI execution paths
must be unreachable from the new host, including nested derivation calls.

## 5. Cross-cutting contracts

### 5.1 Execution, source isolation, and artifact publication

1. Preflight the approved core pin, Python interpreter, Copilot authentication,
   configured models, clean source checkout, command policy, and budgets.
2. Create a host-owned worktree at the recorded source commit. Stage explicitly
   selected prior artifacts/documents when needed; never silently replace the
   requested source with a different checkout.
3. Agents inspect and modify only authorized run paths. The pinned core is
   read-only. Original source is read-only; only the host publishes approved
   generated quality artifacts back to the selected target.
4. Guard Windows path traversal, case aliases, symlinks/junction escapes,
   unsafe argument substitution, and commands outside approved working roots.
   Resolve executables and arguments without an unrestricted shell.
5. Default-deny SDK built-in shell/file/URL tools and unsolicited MCP servers,
   hooks, or automatic skill loading. Prefer controlled host functions.
   Prove the chosen SDK can enforce this, including repository instruction
   isolation for personas and verification agents.
6. Record each process's executable, arguments, working directory, duration,
   stdout/stderr, exit status, timeout, and cancellation evidence. Stop only
   owned processes/descendants; never kill by global process name.
7. Keep a patch-application receipt and restore only changes owned by the
   current verification attempt. Preserve evidence if cleanup cannot be
   verified; do not perform a broad reset or pretend cleanup succeeded.
8. Publish complete validated artifact snapshots with a recoverable receipt.
   Prevent overwriting a newer target run or discarding previous operator
   confirmations. Retain failed-run evidence.

`qpb_install` is a separate, explicitly authorized deployment operation: it may
write QPB's installation/scaffolding files and backups, not product fixes.
Report those changes; never auto-commit or discard them to satisfy the clean
checkout precondition. Audit-time installation runs inside the owned worktree.
Generated root-level managed instruction blocks are retained as artifacts/
patches for operator adoption, not silently applied to the original source.

**Worktree isolation is not a security sandbox.** Approved repository code can
still access the Windows user's resources or network. The first release is
for trusted repositories; policy denial covers host/agent-authorized operations,
not kernel-level confinement of arbitrary test code.

QPB's iteration reference expects ordinary online test execution and an online
retry before dependency-resolution-based `NOT_RUN`. If network approval is
missing, request it and pause. An explicit refusal becomes a visible blocker;
do not fake an attempted test, silently force offline mode, or weaken the gate.

### 5.2 Durable jobs and resume

Persist, at minimum:

- MCP `runId`, original repository identity, base commit, worktree identity,
  requested/effective phase groups, iteration plan, recheck lineage, and status.
- Core URL/commit/version, prompt/schema hashes, host/package/checkpoint
  versions, model assignments and effective identities, and policy snapshot.
- Phase attempts, actual completed steps, validator receipts, artifact hashes,
  pending operator requests, patch receipts, publication receipts, errors,
  cancellation requests, and checkpoint references.

Keep the unique MCP job ID distinct from QPB's timestamp-shaped log `run_id`,
with an explicit mapping and collision checks. Preserve QPB's event formats
and centralized log layout; SQLite does not replace those artifacts.

Use a local job lease and a target-repository execution lock to prevent duplicate
dispatch. Validate checkpoints and artifacts against their recorded dependency
and repository identities before resume. Never auto-upgrade an interrupted run
to a new core/model/package set.

MAF checkpoints are additional execution evidence, not the sole completion
oracle. Reconcile unfinished tool/patch operations on restart. Reuse a phase
only when its authoritative artifacts and validators establish completion;
otherwise restart the incomplete phase safely. If provider session recovery
cannot be proved, rebuild context from approved artifacts rather than claiming
continuity. Grouped-context recovery must be verified or explicitly restart
the affected group.

On graceful disconnect, request cancellation, stop owned work, persist evidence,
and mark the job interrupted. On abrupt host death, recover expired leases as
interrupted; never auto-declare success or resume without an operator request.
Explicit cancellation has its own recorded outcome, distinct from disconnect
and substantive validation failure.

### 5.3 Human decisions and independent agents

- Pending input includes a durable request ID, scope, question, allowed response
  shape, and the exact proposed effect. `qpb_resume` accepts explicit replies
  only for matching pending requests; reject stale or duplicate approvals.
- Preserve user-reviewed statements/transcripts as citable evidence and maintain
  append-only operator confirmations. MAF agents, classifiers, and personas
  cannot manufacture `operator-confirmation` provenance.
- Exercise Visual Studio's actual confirmation behavior before treating a
  reply as human authorization. If the client path cannot distinguish the
  required operator act from an agent-authored answer, block that capability
  and obtain an explicitly approved interaction change.
- Personas receive staged documents/spec/rubric only: no implementation,
  credentials, confirmation ledger, shell, or fetch tools. Apply existing
  grounding/merge/renumber logic; label their provenance `agent-validation`.
- Council members see their prescribed common inputs, not one another's
  conclusions. Record three distinct resolved models, separate session IDs,
  assignments, and failures. Do not claim vendor independence.
- A roster change invalidates the affected Council and citation-review outputs
  and downstream verification. Keep the historical attempt; rerun the required
  Council stages consistently instead of combining incompatible votes.
- Phase 6 always receives a fresh MAF session. It cannot fix the executor's work
  or override process receipts; its narrative is not the gate verdict.

### 5.4 Completion and reporting

Separate job lifecycle from quality outcome. Proposed lifecycle values include
running, awaiting input, blocked, interrupted, cancelled, completed, and failed;
progress reports actual steps, not fabricated percentages.

| Evidence | Quality outcome |
|---|---|
| All requested full-run work, clean gate verdict, and required validators passed | Passed |
| Exact cleanup-needed gate verdict and required validators passed | Passed with cleanup needed |
| Substantive gate failure or required validator failure | Failed |
| Subset/recheck without full verification, blocked input, missing verdict, timeout, cancellation, or incomplete execution | Not evaluated as a successful full audit |

Both clean pass and cleanup-needed can exit zero. Parse and retain the literal
gate verdict as well as the exit code. Missing/malformed/conflicting verdicts
are explicit execution errors. Align INDEX fields with the pinned schemas and
validators after resolving the known prose conflict.

A validator failure stops dependent work. Route repair through an explicit new
execution attempt, then run a fresh verifier again; never let the verifier fix
its own audit subject. Presentation preserves bug findings even when cleanup
or infrastructure issues prevent a clean final outcome.

## 6. MCP operation coverage

All tool inputs/results are typed and versioned. Use run-scoped artifact IDs,
not arbitrary read paths. Reject unsupported options and disclose partial
milestone capability; do not silently perform a smaller audit.

| Tool | Responsibility | First usable increment |
|---|---|---|
| `qpb_install` | Invoke the pinned canonical installer in the authorized run/target layout, preserve backups and attribution, and report its event output truthfully. | M2/M3 |
| `qpb_validate` | Invoke deterministic install/layout validation, return emitted findings and remediation; no silent cross-checkout repair. | M2/M3 |
| `qpb_run` | Preflight options, persist an accepted job, return `runId` without awaiting the audit, and dispatch the MAF workflow. | M3; full parity M8 |
| `qpb_resume` | Reconcile saved evidence, accept scoped operator replies, validate compatibility, and continue the next valid step. | M3/M4 |
| `qpb_recheck` | Start a tracked prior-bug recheck, not a new discovery run. | M8 |
| `qpb_get_status` | Return lifecycle, phase/attempt, iteration, completed steps, pending input, blockers, and quality outcome. | M3 |
| `qpb_list_artifacts` | Return actual registered artifacts with IDs, kind, size, hash, attempt/iteration, and availability. | M3 |
| `qpb_get_artifact` | Read bounded report content by artifact ID, with explicit pagination/truncation and access checks. | M3 |
| `qpb_cancel` | Persist an idempotent cancellation request and expose eventual stop/cleanup status; not instant completion. | M3 |

Keep stdout exclusively MCP protocol traffic. Route host, Python, SDK, and
attribution output to captured evidence/stderr or structured tool results.
Never prompt with `Console.ReadLine` on the MCP transport.

## 7. Implementation increments and gates

Increment IDs are migration milestones, not QPB phase numbers.

### M0 - Freeze the behavioral contract and acceptance baseline

**Depends on:** none.

**Deliver:**
- Resolve the upstream v1.6.0 release ref, verify immutable commit and metadata,
  establish the separate host repository, and record the dependency lock.
- Inventory every AI execution seam, deterministic utility, prompt, schema,
  phase prerequisite, grouping/default option, and generated artifact.
- Select the .NET and non-.NET acceptance targets and exact commits; supply
  required corpora/toolchains. Capture their reproducible baseline results.
- Record contract contradictions and approved compatibility deltas. Reconcile
  stale prose against pinned schemas/validators before implementing transitions.
- Obtain the remaining operational inputs and an explicit live-call/budget policy.

**Verify:** repeatable source acquisition with Windows symlink handling,
complete import/resource closure, baseline tests and golden artifact fixtures,
and dependency/license attribution. Distinguish missing prerequisites from defects.

**Stop/go:** approved immutable source, complete contract map, selected targets,
and explained baseline failures. A floating branch or absent required corpus
does not pass this gate.

### M1 - Prove the .NET MAF/Copilot execution and permission seams

**Depends on:** M0.

**Deliver:** a bounded feasibility spike with exact .NET/MAF/Copilot package and
runtime pins. Create Copilot-backed `AIAgent` instances and execute a real custom
tool through MAF; do not substitute direct SDK-only phase execution.

**Verify:**
- Authentication, explicit model selection/availability, reported identity,
  distinct fresh sessions, streaming/results, and provider failure surfaces.
- Permission denial for SDK built-ins and approval enforcement for custom tools;
  test the documented pre-tool-hook override hazard.
- No unsolicited repository hooks, skill loading, or extra MCP capabilities.
- Cancellation, process ownership, stdio disconnect, pending approval, and
  checkpoint/provider-session behavior across a host restart.
- A denied tool/unknown model/malformed provider result never becomes success.

**Stop/go:** an exact compatible package set and demonstrated controls. If model
identity, input isolation, durable approvals, or cancellation cannot meet the
chosen contracts, report the blocker for operator resolution before expansion.

### M2 - Integrate deterministic Python utilities and controlled tools

**Depends on:** M0 and M1. Deterministic adapter work can start after M0 in
parallel with the provider spike; completing its live MAF gate requires M1.

**Deliver:**
- A small typed Python adapter for canonical install, validation, ingestion,
  citation/assembly, state, and artifact operations; preserve their output.
- Controlled repository read/write, patch, and approved build/test tools with
  cancellation, budgets, Windows-safe path checks, and execution receipts.
- A MAF execution seam for nested Python AI requests. Prefer existing
  classifier/response and plan/assemble interfaces. Where synchronous
  `LLMRunner.run` cannot consume precomputed responses, implement a narrowly
  scoped request/response adapter to host-dispatched MAF sessions, not AI CLIs.
  Avoid re-entering a suspended caller agent's tool loop.
- Minimal core changes only where needed, with a change manifest and regression
  tests. Resolve legacy CLI/environment checks for an explicit MAF host path;
  do not impersonate an old execution mode or disable artifact enforcement.

**Verify:** direct pinned-Python versus adapter result parity; missing Python,
malformed events, partial install, timeouts, cancellation, path/junction escape,
argument injection, unapproved commands, and denied network requests.
Exercise nested reasoning through MAF and assert no one-shot AI CLI launch.

**Stop/go:** deterministic receipts remain faithful and authoritative; all AI
seams have a demonstrated MAF route or an explicit blocking work item.

### M3 - Ship the tracked MCP job lifecycle and Phase 1 vertical slice

**Depends on:** M1 and M2.

**Deliver:**
- Windows stdio host, thin command handlers, SQLite job state, durable checkpoint
  storage, target locks, pending input, artifact access, and controlled shutdown.
- Install/validate plus a tracked Phase-1-only `qpb_run`, resume/status/artifact/
  cancellation operations. Mark this an explicit subset, not a full audit.
- MAF exploration using original phase instructions, documentation intake,
  classifier reads, role mapping, provenance, and Phase 1 validation.
- Preserve three-lane document authority: structurally validated contracts,
  disclosed unconfirmed prose, and operator-confirmed flagged/self-authority
  content. Do not let included document text approve itself.
- Define the install layout and `PYTHONPATH` against the real pinned closure;
  do not assume the existing validator already recognizes MAF-only hosts.

**Verify:** `qpb_run` returns a persisted `runId` while a deliberately blocked
phase task remains incomplete; the job is then queryable and cancellable.
Exercise crash/restart, lost responses, duplicate resume, genuine operator
confirmation, conflicting jobs, artifact traversal, and MCP stdout cleanliness.
Assert the original source is unchanged.

**Stop/go:** a real Phase 1 slice works from Visual Studio, resumes truthfully,
and preserves validator/provenance contracts on both selected target types.

### M4 - Preserve Phase 2 generation, human validation, and personas

**Depends on:** M3.

**Deliver:** MAF generation with original requirements/tests/review protocols;
manifest/render contracts, RUN_CONTRACT separation, traceability, coverage/gaps,
requirements interview, append-only confirmations, and isolated persona
remediation. Reuse deterministic grounding/merge/renumber helpers.

**Verify:** golden schema/contract fixtures and mutation failures; unchanged
record/citation attachment except explicitly permitted changes; human answers
round-trip into citable transcripts; confirmations survive re-derivation.
Test persona source/secret/network denial, poisoning, candidate-only ungrounded
adds, conflict handling, and `agent-validation` versus human provenance.

**Stop/go:** Phase 2's required artifact set and validator pass; no manufactured
human confirmation or source-fed persona. Static golden files alone do not
prove live prompt fidelity: perform the corresponding live generation checks.

### M5 - Preserve Phase 3 three-pass review and derivation/divergence

**Depends on:** M4.

**Deliver:** the original three-pass review protocol, confirmed-bug writeups,
regression patches, and applicable skill-as-code derivation/divergence behavior.
Route every nested model request through the MAF seam established in M2.

**Verify:** language-appropriate review fixtures and known-defect/negative
controls; complete traceability and real regression tests, not stubs.
Instrument process launches to prove Python derivation cannot fall back to
Claude/Copilot/Codex/Cursor phase CLIs.

**Stop/go:** required review artifacts and prerequisites pass for Code/Skill
roles as applicable. Unsupported required nested reasoning blocks the run.

### M6 - Preserve Phase 4 independent Council and citation review

**Depends on:** M5.

**Deliver:** three explicitly assigned, mutually blind MAF auditors; original
audit/triage/probe contracts; net-new regression tests; same-roster Layer-2
semantic citation review using existing deterministic prompt/assembly helpers.
Bind Python Council assembly to the recorded run roster without altering the
operator's global QPB configuration.

**Verify:** distinct effective model/session identities; no peer conclusions
in initial inputs; missing/duplicate/replaced model failures; majority
overreach handling; malformed/incomplete responses; stable reviewer IDs across
spec audit and citation review; approved roster-change invalidation.

**Stop/go:** all three configured reviewers actually ran with verifiable
assignments and valid outputs. Unavailable independence blocks the stage;
three instances of one model or a two-member audit never pass it.

### M7 - Preserve Phase 5 TDD and Phase 6 authoritative verification

**Depends on:** M6.

**Deliver:**
- Reconciliation of every finding, completeness reporting, runner probes,
  actual red/green test execution, exemptions, patch receipts, and cleanup.
- A separately created fresh-context MAF verifier using the original audit
  instructions and deterministic mechanical checks, full gate, and phase
  validator. Persist literal process evidence and map all three gate outcomes.
- Final INDEX/progress/report contracts and host-controlled artifact publication.
  Any executor-owned finalization precedes the independent check or triggers
  a recheck of affected evidence; the verifier never repairs failures.
- Group-context support with mandatory independent Council/Phase 6 sessions.

**Verify:** real failing regression on unpatched code and passing regression
with a valid fix; unavailable runners; denied dependency restoration; failed
patch apply/reverse; interrupted verification; preserved original source.
Mutate the gate/validator outputs to prove an agent's PASS narrative cannot
override failure, missing execution, or a cleanup-needed verdict.

**Stop/go:** successful, cleanup-needed, and substantive-failure fixtures map
correctly. Final success requires all authoritative checks, not exit zero alone.

### M8 - Complete execution-option parity, iterations, and recheck

**Depends on:** M7.

**Deliver:**
- Full run: phases 1-6 followed by gap, unfiltered, parity, and adversarial.
  Also explicit valid phase subsets/groups and ordered iteration selections.
- Preserve shared context for requested working-phase groups where valid;
  disclose Phase 6's forced fresh-context split and retain per-phase gates.
- Iteration plan, numbered/merged exploration, demoted candidates, cumulative
  traceability, and renewed phases 2-6/TDD. Never clear the quality tree simply
  because another iteration starts.
- `qpb_recheck`: inspect only previously reported bugs, use existing patch/test
  workflow, and emit recheck schema 1.0 results and summary with `FIXED`,
  `PARTIALLY_FIXED`, `STILL_OPEN`, or `INCONCLUSIVE`. No new-bug discovery.
- Phase 7 presentation/drill-down and improvement choices via MCP artifacts
  and status, without automatically applying fixes to the original source.
  Preserve the post-verification managed AGENTS output in the worktree and
  return its adoption patch alongside the reports.

**Verify:** option/dependency matrix, malformed plans, missing prerequisite
artifacts, grouped context and restart, all four strategy contracts, real TDD
for new iteration findings, recheck status fixtures, and cancellation cleanup.
Do not require identical stochastic prose or bug counts for parity.

**Stop/go:** all nine MCP operations and the full behavioral matrix are
implemented; subset/recheck results cannot be mistaken for a full verified run.

### M9 - Acceptance, Windows packaging, and operational handoff

**Depends on:** M8.

**Deliver:** documented Visual Studio configuration, exact dependency/package
locks, Python/Copilot prerequisite checks, architecture/interaction/safety
documentation, attribution/licenses, and an operator-approved Windows
distribution format. Package/provision the complete pinned dependency
reproducibly; never fetch a floating checkout during a quality run.

**Verify:**
- Host unit/contract tests, deterministic Python compatibility tests, and
  actual MCP transport tests with a fake long-running workflow.
- End-to-end live runs on the approved .NET and non-.NET repositories:
  methodology/artifact contracts, independent Council receipts, seeded-defect
  detection and negative controls, genuine TDD, final outcome mapping,
  worktree-only edits, and all iteration/recheck operations.
- Fault injection at tool, phase, checkpoint, publication, and shutdown
  boundaries; restart without duplicate side effects or false completion.
- Fresh Windows install and Visual Studio invocation, including paths with
  spaces, required symlink handling, permissions, and stdio EOF.
- Operator-approved cleanup/retention; no credentials in reports or distributable
  logs, no generic shell MCP tool, and no unapproved legacy AI executor.

**Stop/go:** no unexplained migration regressions relative to M0; all required
positive/negative/fault controls pass; real validator evidence supports the
outcome. Benchmarks that could not execute are disclosed blockers, not waived
by a structural test suite.

## 8. Dependency order and scope limits

```text
M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9
 |          ^
 +----------+  deterministic M2 work may begin before M1 completes
```

The first usable increment is a clearly labeled Phase 1 subset, not a
"completed Quality Playbook migration." Full-release acceptance is M9.

No cloud hosting, HTTP transport, provider-neutral agent framework, detached
worker, multi-job scheduler, automatic original-source fix application, or OS
sandbox is included in the first release. Add any of these only after a new
operator decision and a demonstrated need. No schedule, cost, model roster,
or arbitrary performance threshold is invented by this plan.
