# Quality Playbook: MAF/Copilot MCP Migration Implementation Plan

## 1. Purpose and status

**Planning handoff, not an implementation or a claim of runtime compatibility.**
This revision consolidates the original plan after it was verified against the
repository, the published compatibility-fork tags, and the official Microsoft
and Claude Code documentation (Appendix A lists every correction; Appendix B
lists what was and was not verified). The architectural decisions below were
clarified with the operator. Implementation increments have explicit evidence
and acceptance gates.

Build a separate .NET 10 application that exposes Quality Playbook operations
over local stdio MCP, runs on Windows and Debian 13 (Trixie) on x86-64, and is **installed
as a .NET tool**. Microsoft Agent Framework (MAF) owns the quality workflow and
its agents perform all AI reasoning through the GitHub Copilot SDK. The
supported MCP clients are Visual Studio Code Copilot Chat and Claude Code.
They only call the host's tools; **a Claude Code client does not make Claude
the reasoning provider**, and the legacy Claude/Codex/Cursor runners stay
unreachable. Consume the complete Python Quality Playbook (QPB) source tree as
a pinned Git dependency; preserve its methodology, prompts, deterministic
utilities, schemas, validators, generated artifacts, and Apache 2.0
attribution.

This is **not** a generic autonomous coding agent, a rewrite of QPB in C#, or
an MCP wrapper that delegates reasoning to the existing external-AI-CLI runner.

**Progress already on record (verified in this checkout):**

- The QPB compatibility fork exists as annotated tags `v1.6.0-maf.1`
  (`23a5067`) and `v1.6.0-maf.2` (`1319df0`) on
  `https://github.com/svolmer/quality-playbook`, based on upstream v1.6.0
  (`400f66f`). Its manifest (`COMPATIBILITY_FORK.md` at the tag) closes
  contradictions CC-01 through CC-21. The tags are not ancestors of `main`;
  the branch the manifest names (`compat/v1.6.0-maf`) did not exist locally or
  on `origin`; it was created at `1319df0` and published on 2026-10-20, then
  rebased onto `main` by the operator. The rebased commits carry identical
  changes and every runtime path is byte-identical to `1319df0`; the host pin
  stays `1319df0` (see `COMPATIBILITY_FORK.md`, "Branch history").
- The manifest refers to host-repo files (`docs/m0/contract-contradictions.md`,
  `docs/m0/baseline/`, `deps/quality-playbook.lock.json`). **That host
  repository could not be found** (not on disk, not on the `svolmer` GitHub
  account), so a new host repository was created for M0 (now private at
  `github.com/svolmer/QualityPlaybook.Agent`) and the manifest's host artifacts
  were reconstructed. See section 8, M0.
- No .NET production code, projects, or tool package are known to exist.
- The fork's test baseline was recorded on a Windows host only (section 3).

## 2. Confirmed operator decisions

| Area | Confirmed decision |
|---|---|
| Repository topology | Separate .NET repository consuming a pinned QPB dependency. |
| First-release platform | Windows and Linux; Visual Studio Code Copilot Chat & Claude Code; local stdio MCP. **Linux scope resolved 2026-10-20: Debian 13 (Trixie) on x86-64.** |
| Framework | .NET 10 LTS. |
| **Installation** | **The host is installed as a .NET tool (`dotnet tool install`). It is the only supported install channel.** See section 5. |
| Preview packages | Permitted, with exact tested package versions pinned. |
| Dependency form | Pinned Git source dependency retaining the complete QPB core tree, not a piecemeal copy or package-only closure. Git is the build-time form; the tool package embeds that exact tree at run time (section 5). |
| Dependency pin | Upstream v1.6.0 (`400f66f`) is the verified base. The active pin is the compatibility fork commit `1319df0` (`v1.6.0-maf.2`) unless a later fork tag supersedes it. Pin by commit hash, never by tag or branch name. |
| Compatibility changes | Minimal, tested, documented changes in the pinned QPB fork; preserve methodology, prompts, schemas, and validators. Each change is listed in the fork manifest against a contradiction ID. |
| Source isolation | Apply test/fix changes in an isolated Git worktree. Leave the original source untouched and return patches. |
| Dirty source | Require a clean source checkout before creating the audit worktree. |
| Job lifetime | Stop safely on stdio/client exit; support explicit resume after MCP host restart. No detached worker for the initial release. |
| Concurrency | One active quality job per host; never execute two jobs for the same target repository. |
| Durable state | SQLite host state plus separately persisted MAF checkpoint payloads; retain existing QPB JSONL logs. |
| Council roster | Explicit operator-supplied roster for every run; no host default. The host never falls back to QPB's built-in default roster. |
| Council independence | Three distinct resolved model IDs and separate, mutually blind contexts. Different vendors are not required. |
| Council unavailability | Block the Council stage. Changing the roster requires explicit operator approval before resume. |
| Human input | Pause with an awaiting-input status; Copilot Chat or Claude Code submit explicit operator answers through `qpb_resume`. Section 6.3 adds the per-client verification this depends on. |
| Commands | Operator-approved per-repository executable/argument allowlist, checked before every invocation. |
| Repository network access | Deny by host/tool policy by default; explicit run-scoped approval for restores, installation, or other network operations. Copilot provider connectivity is a separate required permission. |
| Trust scope | Trusted local repositories only. Child processes are not OS-sandboxed; disclose this limitation rather than claiming network/filesystem confinement. .NET tools also run in full trust (Microsoft documentation), so the same disclosure covers the tool. |
| Grouped verification | Accept requested phase groups, but always split Phase 6 into a fresh-context verifier and disclose the effective grouping. |
| Acceptance target | **`spectreconsole/spectre.console` tag `0.57.2`, commit `bbbb5729dde27b58deee44f447a788eea46ee451`** (operator, 2026-10-20). No non-.NET target is required, so acceptance covers C# only and QPB's other-language behavior stays inherited and unverified. Acceptance runs on both supported operating systems (M9). |
| Source-contract conflicts | Reconcile stale prose with schemas and executable validators in the compatibility fork before proceeding. **Done for CC-01..CC-21 in the fork; the host-side deltas in section 5.4 remain.** |
| Plan location | Store this handoff in the current QPB checkout. Do not create or modify the future .NET repository from this plan. |

### Inputs deliberately not invented here

The following are not assigned speculative values. Resolve them at the
indicated increment or obtain explicit operator configuration before the
relevant run. An unavailable required input produces a visible configuration
blocker.

NuGet package versions, ordinary phase model assignments, the three Council
model IDs, benchmark repositories/commits, approved commands, execution
budgets, state/worktree locations, retention policy, the **NuGet feed that
hosts the tool packages** (nuget.org, a private feed, or a folder source), the
runtime identifiers if the package must be RID-specific (`win-x64` and
`linux-x64`; the Linux scope is fixed at Debian 13 on x86-64), and the choice of
operator-confirmation channel (section 6.3). The tool package ID and command
name are proposed in section 5.1 and confirmed in M1.

## 3. Ground truth and feasibility evidence

### QPB sources

Contract authority is the **pinned dependency**, not this checkout's `main`.
`main` is at `1001b38`, which is ahead of v1.6.0 (it merges the 1.6.1 campaign
evidence) and does **not** contain the fork's fixes. Links below are for
navigation; read the pinned versions when implementing.

- [SKILL.md](../../SKILL.md): operational phase chain, artifact contracts,
  attribution, execution modes, and presentation.
- [v1.6.0 design](QPB_v1.6.0_Design.md): sections 5 and 6 (coherence and human
  validation), section 8/F-2a (durable confirmations), section 8a and its
  2026-07-25 revision (three-lane classification), and section 8b (isolated
  persona remediation). Do not implement the superseded mechanical genre-floor
  design or import the deferred v1.6.1 precision scope.
- [v1.6.0 implementation plan](QPB_v1.6.0_Implementation_Plan.md) and
  [development process](../../ai_context/DEVELOPMENT_PROCESS.md): source
  precedence, fixture acceptance, invariants, and truthful release evidence.
- [Existing runner](../../bin/run_playbook.py): phase selection
  (`--phase`, `--phase-groups`), iteration (`--next-iteration`, `--strategy`),
  and grouped contexts. It is a behavioral reference, **not the new
  executor**. Its prompt text for iterations is reused by the host (CC-16).
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
  and [Council semantic checks](../../plugins/quality-playbook/skills/quality-playbook/scripts/council_semantic_check.py).
- [Install validator](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_validate.py),
  [phase validator](../../plugins/quality-playbook/skills/quality-playbook/scripts/validate_phase_artifacts.py),
  [quality gate](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py),
  and [fresh auditor prompt](../../plugins/quality-playbook/skills/quality-playbook/phase_prompts/phase6_auditor.md).
- Fork manifest: `COMPATIBILITY_FORK.md` at tag `v1.6.0-maf.2`
  (`git show v1.6.0-maf.2:COMPATIBILITY_FORK.md`).

### Contract conflicts: status

Two conflicts recorded in the first revision of this plan are **resolved in the
fork** and still present on `main`:

| Conflict (as found on `main`) | Resolution in the fork |
|---|---|
| Run-state schema said INDEX.md "was never adopted", yet the validator and auditor require it. | CC-05 (`maf.1`): Phase 6 completion requires `quality/INDEX.md` with a parsed, non-`pending` `summary.gate_verdict`. |
| `pass-with-cleanup` missing from the auditor's verdict enumeration (`phase6_auditor.md` on `main` still lists `pass`/`partial`/`fail`). | CC-02/CC-03 (`maf.1`): enum has four values; auditor cross-checks INDEX `gate_verdict` against the witnessed `RESULT:` line; mismatch is FAIL. |

The fork also fixes the Phase 6 ownership gap (CC-03: executor runs
`finalize-index`, the auditor never repairs) and the AGENTS.md deadlock
(CC-15). It strengthens two gate checks (CC-17 recheck statuses and counts,
CC-19 `agent-validation` ledger lines). It deliberately leaves two residual
risks to the host: a forged `operator-confirmation` ledger line still passes
the gate, and the code accepts any non-empty Council roster.

### Baselines

- The first revision cited a 148-test representative run on `main` (142 passed,
  3 failed, 1 errored, 2 skipped); that figure is confirmed in
  [test evidence](../codebase/TESTING.md) but is **superseded** as a migration
  baseline. The fork manifest records full-suite comparisons against upstream
  `400f66f`: baseline 3055 tests / 54 failures / 5 errors / 47 skipped;
  `maf.1` 3078 / 54 / 6 / 48; `maf.2` 3106 / 54 / 6 / 48. All failures match
  the baseline set except one environmental error: a test that spawns bare
  `python3`, which on the Windows host resolves to the Python install-manager
  alias and times out.
- **That baseline is Windows-only.** Debian 13 needed its own baseline; it was
  captured in M0 and fails 19 tests against Windows' 54, so the known failures
  are not identical across operating systems.
- The fork recorded no benchmark-repo runs (no live AI calls were permitted
  during that phase). Acceptance targets still need baselines in M0.

### Official runtime documentation

Verified on 2026-10-20 unless marked otherwise (Appendix B):

- [Learn: GitHub Copilot agents](https://learn.microsoft.com/agent-framework/integrations/by-component/agent-services/github-copilot):
  .NET package `Microsoft.Agents.AI.GitHub.Copilot`; `CopilotClient` +
  `AsAIAgent`; by default shell, file, and URL tools are denied until
  `SessionConfig.OnPermissionRequest` is supplied. The SDK owns the
  tool-calling loop; approval for custom tools is enforced through its
  `OnPreToolUse` hook. **A custom `SessionConfig.Hooks` hook replaces the
  default approval hook**, so approval enforcement must be tested, not
  assumed. The page states that "some SDKs use an installed CLI" and
  recommends containers for agents with shell/file permissions.
- [Learn: workflow checkpoints](https://learn.microsoft.com/agent-framework/workflows/checkpoints):
  checkpoints are written at the end of each superstep and capture executor
  state, pending messages, pending requests/responses, and shared state. .NET
  uses `CheckpointManager`, `RestoreCheckpointAsync`, and
  `InProcessExecution.ResumeStreamingAsync`. **A resumed workflow must keep the
  same topology and executor identities; agent-based workflows need stable
  agent `Id` (and `Name`) values.** Storage is a trust boundary. The page shows
  only an in-memory manager for .NET, so a durable store is host work. It does
  not establish exactly-once side effects or Copilot-session recovery.
- [Learn: build a C# MCP server](https://learn.microsoft.com/dotnet/ai/quickstarts/build-mcp-server):
  stdio servers pack as a **tool package plus RID-specific packages** with
  `dotnet pack -c Release`; all `.nupkg` files must be pushed; `server.json`
  drives NuGet's MCP configuration; clients can launch the published package
  with `dnx <PackageId>@<version> --yes`, and `dnx` ships with the .NET 10 SDK.
  The `Microsoft.McpServer.ProjectTemplates` template is preview. The VS Code
  `mcp.json` shape (`servers` → `type`/`command`/`args`/`env`) is shown there.
- [Learn: .NET tools](https://learn.microsoft.com/dotnet/core/tools/global-tools):
  a tool is a NuGet package containing a console app; install modes are global
  (`%USERPROFILE%\.dotnet\tools` on Windows, `$HOME/.dotnet/tools` on
  Linux/macOS), `--tool-path`, and local manifest (`.config/dotnet-tools.json`,
  restored by `dotnet tool restore`); `dotnet tool update` uninstalls and
  reinstalls the latest stable version; tools run in full trust; tools might
  not work if .NET was installed via Snap.
- [Claude Code: MCP](https://code.claude.com/docs/en/mcp) (first 100,000 of
  about 123,000 characters read): stdio servers are added with
  `claude mcp add --transport stdio [--scope local|project|user] <name> -- <command> [args...]`;
  the project file is `.mcp.json` with top-level key **`mcpServers`** (VS Code's
  format uses **`servers`**; do not copy between them). In `claude -p`, Agent
  SDK, and cloud sessions project-scoped servers load without an approval
  prompt, and `bypassPermissions` mode can skip it too. MCP elicitation is
  supported.
- [VS Code: MCP servers](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)
  (summary only; the configuration reference was not retrieved): VS Code format
  uses `servers`; `.vscode/mcp.json` and user-profile `mcp.json` exist (marked
  deprecated in the guided flow in favor of a Copilot-level configuration file);
  tool approval is interactive; servers that need interactive inputs are not
  forwarded to Copilot harness sessions; elicitation support is not stated.
- [Learn: MCP tools with agents](https://learn.microsoft.com/agent-framework/agents/tools/local-mcp-tools):
  describes agents consuming MCP tools; not a recipe for this application's
  public MCP server.

These sources establish feasibility candidates, not compatibility of a chosen
package set. No live provider authentication, model availability, tool-package
install, or restart experiment has been performed.

## 4. Proposed module structure and ownership

Use the requested four-project structure as the starting proposal, not a
generic agent platform or an extra project for each command:

```text
QualityPlaybook.Agent.sln
  src/
    QualityPlaybook.Mcp/            stdio MCP host; packed as the .NET tool
    QualityPlaybook.Orchestration/
    QualityPlaybook.AgentRuntime/
    QualityPlaybook.Core/
  tests/
    QualityPlaybook.Core.Tests/
    QualityPlaybook.Orchestration.Tests/
    QualityPlaybook.Mcp.Tests/
    QualityPlaybook.Packaging.Tests/   install/launch smoke from the .nupkg, per OS
  external/
    quality-playbook/               Git submodule at the pinned commit (build input)
  deps/
    quality-playbook.lock.json      URL, commit, skill version, fork tag, payload hash
  docs/
    architecture.md
```

- **Mcp module:** transport, input validation, thin operation handlers, and the
  tool entry point (section 5.1). No quality-review prompts, phase decisions,
  shell interface, or reasoning.
- **Orchestration module:** the small command interface, MAF workflow
  coordinator, phase/group dependencies, Council dispatch, validator-driven
  transitions, durable job state, artifact publication, and recovery.
- **AgentRuntime module:** Copilot-backed MAF agents and controlled execution
  tools, including the deterministic Python adapter. Its seams support live
  execution and test doubles; do not introduce interchangeable providers.
  OS-specific code (process ownership, path normalization, interpreter
  discovery) lives behind one small seam here, not scattered.
- **Core module:** typed run/options/results and application contracts. It is
  **not** a C# replacement for Python QPB's core.
- **Pinned Python dependency:** owns deterministic methodology contracts.
  The submodule is the build-time source; the lock file records URL, commit,
  skill version (`1.6.0`), fork tag, `compatibilityFork` identity, and the
  embedded payload's content hash. The fork keeps skill version `1.6.0`
  (a suffix would break the gate's version-stamp checks), so **the commit hash
  and fork tag, not the version string, identify the dependency.**

Workflow scheduling and tool execution remain host-owned. The SDK owns its
documented internal tool-calling loop, operating only with the permissions and
tools the host authorizes. Agents cannot invoke the public lifecycle tools to
approve themselves or launch additional quality jobs. **Gate and validator
commands are executed by deterministic host code, never by an agent**, which
structurally prevents the AGENTS.md-documented failure where a sub-agent hid
the gate invocation and a PASS was fabricated against a failing gate.

The SDK may launch or connect to its documented Copilot CLI server transport.
That is distinct from launching `copilot -p`, `gh copilot --prompt`, Claude,
Codex, or Cursor as one-shot phase executors. Those legacy AI execution paths
must be unreachable from the new host, including nested derivation calls.

## 5. Distribution and installation (.NET tool)

**Requirement: installation MUST be via `dotnet tool`.** Consequences:

### 5.1 Package and entry point

- The `QualityPlaybook.Mcp` project is packed with `PackAsTool` as a NuGet tool
  package. Proposed (confirm in M1): package ID `QualityPlaybook.Agent`,
  command `qpb-agent`. Confirm in the M1 spike that the template-generated
  project properties for tool and `McpServer` package type are applied; this
  pass read the documentation, not a generated `.csproj`.
- Entry point: `qpb-agent serve` runs the stdio MCP server; stdout carries
  protocol traffic only. `qpb-agent --version` and `qpb-agent doctor` are
  human-facing and never run inside the MCP transport. `doctor` performs the
  preflight in section 5.3 and is the installation verification command.
- Include an MCP `server.json` so the package is discoverable with the MCP
  package type.
- Packaging: **RID-specific, decided by M1 evidence.** The Copilot SDK downloads
  and bundles its runtime (208 MB raw) per RID at build time, so `dotnet pack`
  emits a pointer package plus `win-x64` (101 MB) and `linux-x64` (109 MB)
  packages, and `dotnet tool install` selects the right one. **All three must be
  published together.** Native AOT is not assumed; MAF and the Copilot SDK are
  unverified for AOT. On Windows the tool also installs a `qpb-agent.cmd` shim, so
  client configs use the absolute `qpb-agent.exe` path that `doctor` prints.

### 5.2 Installation modes and client configuration

| Mode | Command | Status |
|---|---|---|
| Global (canonical) | `dotnet tool install -g QualityPlaybook.Agent --version <exact>` | Supported. |
| Tool-path | `dotnet tool install QualityPlaybook.Agent --tool-path <dir> --version <exact>` | Supported; enables side-by-side versions for resuming an interrupted job. |
| Local manifest | `dotnet tool install QualityPlaybook.Agent` with `.config/dotnet-tools.json` | Supported; the checked-in manifest must pin the exact version. |
| `dnx` | `dnx QualityPlaybook.Agent@<exact> --yes` | Permitted only as a launcher of the same pinned package; it contacts the feed on first run, so it is not the reproducible default. |
| Python/pip, copying the QPB clone, `bin.install_skill` from another checkout, a distro package, or .NET installed via Snap | none | **Unsupported.** The QPB pip layout intentionally makes `import bin` fail, but the host needs the `bin` package (for example `python -m bin.quality_playbook finalize-index`). |

Client configuration names the installed command. The two clients use
**different top-level keys**:

```json
// VS Code: .vscode/mcp.json (or the user-profile / Copilot configuration)
{ "servers": { "quality-playbook": { "type": "stdio", "command": "qpb-agent", "args": ["serve"] } } }

// Claude Code: .mcp.json at the project root, or
//   claude mcp add --transport stdio --scope project quality-playbook -- qpb-agent serve
{ "mcpServers": { "quality-playbook": { "type": "stdio", "command": "qpb-agent", "args": ["serve"] } } }
```

The global tools directory is added to `PATH` when the SDK first runs, so a
client started earlier (or a GUI-launched editor on Linux that did not read the
shell profile) may not see it. `doctor` reports the resolved command path; the
documented fallback is the absolute tool path in the client configuration. M9
verifies both clients on both operating systems.

### 5.3 Embedded QPB payload, Python, and Copilot prerequisites

- **Payload:** the tool package embeds the pinned QPB tree produced by
  `git archive` of the locked commit (tracked files only, no hand-picked
  subset), built on one CI operating system from the commit itself and not from
  a working tree, so Windows `autocrlf` cannot alter file bytes. The measured
  on-disk size of the non-VCS tree in this checkout is tens of megabytes
  (`repos` 3.9 MB, `evidence` 13 MB, `docs/bootstrap` 14 MB); M0 records the
  exact size, confirms it fits the feed's package limit, and records any
  symlink in the archive. The build fails if the embedded hash differs from the
  lock file. At run time the host verifies the payload hash and **never reads
  `external/`, a sibling QPB checkout, or a floating branch.** This implements
  AGENTS.md's anti-scavenge rule (a failed validation HALTs and reports; no
  cross-checkout repair).
- **Read-only payload:** the tool store is treated as read-only on both
  operating systems. Run Python with `PYTHONDONTWRITEBYTECODE=1` (or a
  `PYTHONPYCACHEPREFIX` under the host state directory) so compile-cache writes
  cannot false-fail the install validator, the failure mode behind AGENTS.md's
  090q note. Do not use `python -I`, which ignores `PYTHONPATH`.
- **Python:** not bundled. `doctor` and run preflight resolve an absolute
  interpreter path, check the pinned core's `requires-python` (`>=3.10`), and
  report remediation when it is too old (a Debian-based distribution's default
  `python3` can be older, for example Debian 11 ships 3.9). On Windows resolve
  `python.exe` (for example via the `py` launcher) and reject the Windows
  Store/install-manager alias; never invoke bare `python3` there. On Linux a
  `python3` that satisfies the version check is acceptable, always invoked by
  resolved absolute path.
- **Copilot:** M1 showed the .NET SDK bundles its own runtime (pinned to the SDK
  version: SDK 1.0.14 brings runtime 1.0.85), so **no separate Copilot CLI install is
  needed**. Authentication is picked up from the GitHub CLI (`gh auth login`); `doctor`
  reports the runtime, the signed-in account, and the available models. The tool never
  installs or logs in on the operator's behalf.
- **Attribution:** QPB's attribution banner (AGENTS.md install step 7) is
  returned in `qpb_install`'s structured result and written to stderr, never to
  stdout.

### 5.4 Versioning, updates, and uninstall

- Tool version, embedded payload hash, fork tag, MAF/Copilot package versions,
  operating system, and workflow fingerprint (topology plus executor/agent IDs)
  are recorded on every job.
- **`dotnet tool update` is an operator action, never a host action.** The host
  does not self-update and makes no feed call during a quality run. This
  reconciles the update model (uninstall and reinstall the latest stable) with
  "never auto-upgrade an interrupted run": on resume, a different tool version,
  payload hash, or workflow fingerprint blocks with `incompatible_host`, and the
  result states the exact version to reinstall (use `--tool-path` for
  side-by-side installs) or offers to restart the affected work from approved
  artifacts as a new attempt. Checkpoints created by a different executor
  topology are not resumable (Learn: start a new checkpoint lineage). Job state
  is not portable across operating systems; resume happens on the OS that
  created the job.
- Keep every published tool version available on the feed for as long as
  interrupted jobs may need it (retention is an operator input).
- Job state, checkpoints, logs, and worktrees live **outside the tool store**
  and survive update and uninstall; uninstall never deletes them. Proposed
  defaults, pending operator confirmation: `%LOCALAPPDATA%\QualityPlaybook.Agent`
  on Windows and `${XDG_STATE_HOME:-$HOME/.local/state}/qpb-agent` on Linux.
  Checkpoint storage is a trust boundary: per-user permissions, and a
  checkpoint content hash kept in SQLite.
- Remaining host-side deltas from the fork manifest (not in the fork):
  CC-03 the host's independent verifier applies the same `RESULT:`-line mapping
  and mismatch-is-FAIL rule; CC-15 AGENTS.md is returned as an adoption patch;
  CC-16 iterations run natively with `run_playbook.iteration_prompt` text,
  hash-pinned; CC-19 a per-confirmation host receipt, and a run fails when the
  ledger holds an `operator-confirmation` line without a receipt.

## 6. Cross-cutting contracts

### 6.1 Execution, source isolation, and artifact publication

1. Preflight the tool/payload hash, Python interpreter, Copilot authentication,
   configured models, clean source checkout, command policy, and budgets.
2. Create a host-owned worktree at the recorded source commit. Stage explicitly
   selected prior artifacts/documents when needed; never silently replace the
   requested source with a different checkout.
3. Agents inspect and modify only authorized run paths. The embedded core is
   read-only. Original source is read-only; only the host publishes approved
   generated quality artifacts back to the selected target.
4. Guard path traversal and unsafe argument substitution on both operating
   systems: Windows case aliases and junction/reparse-point escapes; Linux
   symlink escapes and case-distinct names; and, on either OS, a target checked
   out on a filesystem with different case rules. Commands outside approved
   working roots are rejected. Resolve executables and arguments without an
   unrestricted shell.
5. Default-deny SDK built-in shell/file/URL tools and unsolicited MCP servers,
   hooks, or automatic skill loading. Prefer controlled host functions. The
   .NET documentation confirms default denial of shell/file/URL tools only;
   the Python page's statement that workspace `.github/hooks/` are not loaded
   by default is **not** a .NET guarantee, so M1 proves repository hook,
   instruction, and skill isolation for .NET, including personas and verifiers.
6. Record each process's executable, arguments, working directory, duration,
   stdout/stderr, exit status, timeout, and cancellation evidence. Stop only
   owned processes and their descendants (a Windows job object, a Linux process
   group or equivalent; selected in M2); never kill by global process name.
7. Keep a patch-application receipt and restore only changes owned by the
   current verification attempt. Preserve evidence if cleanup cannot be
   verified; do not perform a broad reset or pretend cleanup succeeded.
8. Publish complete validated artifact snapshots with a recoverable receipt.
   Prevent overwriting a newer target run or discarding previous operator
   confirmations. Retain failed-run evidence.
9. **Client-side tool approval is not a control the host relies on.** Claude
   Code can load project servers and run tools without prompts in
   non-interactive or bypass modes; VS Code prompts interactively. The host's
   own policy, receipts, and confirmation channel (6.3) govern.

`qpb_install` is a separate, explicitly authorized deployment operation. It
runs the embedded payload's canonical installer (`bin.install_skill`, with the
payload on `PYTHONPATH`) against the target, may write QPB's installation and
scaffolding files and backups, and reports the installer's `event=` lines
truthfully. It never writes product fixes, never auto-commits or discards its
changes to satisfy the clean-checkout precondition, and the `--ai-tool` value
comes from the operator or the host's own identity, never a guess. Audit-time
installation runs inside the owned worktree. Generated root-level managed
instruction blocks (AGENTS.md) are retained as adoption patches, not silently
applied to the original source.

**Worktree isolation is not a security sandbox.** Approved repository code can
still access the user's resources or network. The first release is for trusted
repositories.

QPB's iteration reference expects ordinary online test execution and an online
retry before dependency-resolution-based `NOT_RUN`. If network approval is
missing, request it and pause. An explicit refusal becomes a visible blocker;
do not fake an attempted test, silently force offline mode, or weaken the gate.

### 6.2 Durable jobs and resume

Persist, at minimum:

- MCP `runId`, original repository identity, base commit, worktree identity,
  requested/effective phase groups, iteration plan, recheck lineage, and status.
- Tool version, operating system, core URL/commit/fork tag/payload hash,
  prompt/schema hashes, host/package/checkpoint versions, workflow fingerprint,
  model assignments and effective identities, and policy snapshot.
- Phase attempts, actual completed steps, validator receipts, artifact hashes,
  pending operator requests, confirmation receipts, patch receipts, publication
  receipts, errors, cancellation requests, and checkpoint references.

Keep the unique MCP job ID distinct from QPB's timestamp-shaped log `run_id`,
with an explicit mapping and collision checks. Preserve QPB's event formats
and centralized log layout; SQLite does not replace those artifacts.

Use a local job lease and a target-repository execution lock to prevent
duplicate dispatch. Validate checkpoints and artifacts against their recorded
dependency, workflow-fingerprint, and repository identities before resume.
Never auto-upgrade an interrupted run to a new tool/core/model/package set.

MAF checkpoints are additional execution evidence, not the sole completion
oracle. Reconcile unfinished tool/patch operations on restart. Reuse a phase
only when its authoritative artifacts and validators establish completion;
otherwise restart the incomplete phase safely. If provider session recovery
cannot be proved, rebuild context from approved artifacts rather than claiming
continuity. Grouped-context recovery must be verified or explicitly restart
the affected group. Agents are created with stable IDs and names so a rebuilt
workflow matches its checkpoints.

On graceful disconnect, request cancellation, stop owned work, persist
evidence, and mark the job interrupted. On abrupt host death, recover expired
leases as interrupted; never auto-declare success or resume without an
operator request. Explicit cancellation has its own recorded outcome.

### 6.3 Human decisions and independent agents

- Pending input includes a durable request ID, scope, question, allowed response
  shape, and the exact proposed effect. `qpb_resume` accepts explicit replies
  only for matching pending requests; reject stale or duplicate approvals.
- Preserve user-reviewed statements/transcripts as citable evidence and keep
  append-only operator confirmations. MAF agents, classifiers, and personas
  cannot manufacture `operator-confirmation` provenance. The fork's gate fails
  `agent-validation` ledger lines but cannot detect a forged
  `operator-confirmation` line, so the host keeps a receipt for every
  confirmation it actually collected and fails any run whose ledger contains an
  unmatched line (CC-19 host delta).
- **Both supported clients let a model call `qpb_resume` itself**, and Claude
  Code can do so without any prompt in non-interactive or bypass modes, so an
  argument string passed to `qpb_resume` is not proof of a human act. Per
  client and per OS, M1/M3 must demonstrate which confirmation channel
  actually reaches the operator and that an agent cannot produce its receipt.
  Candidate channels, to be chosen by the operator and not yet adopted: MCP
  elicitation (documented as supported by Claude Code; VS Code support is not
  established), and an out-of-band `qpb-agent confirm <requestId>` command run
  by the operator in a terminal that writes the receipt directly to host state.
  If neither can be demonstrated for a client, that client's human-input
  capability is blocked and an explicitly approved interaction change is
  required. This refines, and does not replace, the confirmed Human input
  decision.
- Personas receive staged documents/spec/rubric only: no implementation,
  credentials, confirmation ledger, shell, or fetch tools. Apply existing
  grounding/merge/renumber logic; label their provenance `agent-validation`.
- Council members see their prescribed common inputs, not one another's
  conclusions. The host enforces three distinct resolved model IDs (the QPB
  code accepts any non-empty roster, so this is not checked upstream), records
  separate session IDs, assignments, and failures, passes the roster
  explicitly, and never reads QPB's default roster or the operator's global
  `qpb_config`. Do not claim vendor independence.
- A roster change invalidates the affected Council and citation-review outputs
  and downstream verification. Keep the historical attempt; rerun the required
  Council stages consistently.
- Phase 6 always receives a fresh MAF session. It cannot fix the executor's
  work or override process receipts; its narrative is not the gate verdict.

### 6.4 Completion and reporting

Separate job lifecycle from quality outcome. Proposed lifecycle values: running,
awaiting input, blocked, interrupted, cancelled, completed, failed, and
`incompatible_host` as a blocked reason. Progress reports actual steps, not
fabricated percentages.

The completion contract (CC-11, restated by the fork) is: the **last**
`RESULT: GATE …` line of `quality/results/quality-gate.log` (with the `Total:`
line immediately before it, CC-04) is `PASSED` or `PASSED WITH CLEANUP NEEDED`,
**and** `validate_phase_artifacts --phase 6` passed, **and** the INDEX
`summary.gate_verdict` equals the mapping of that witnessed line
(`PASSED`→`pass`, `PASSED WITH CLEANUP NEEDED`→`pass-with-cleanup`,
`FAILED`→`fail`). The executor-owned step that writes the INDEX verdict is
`python -m bin.quality_playbook finalize-index`, run by the host before the
fresh verifier starts; the verifier never repairs.

| Evidence | Quality outcome |
|---|---|
| All requested full-run work, `GATE PASSED`, Phase 6 validation passed, INDEX verdict matches | Passed |
| `GATE PASSED WITH CLEANUP NEEDED`, Phase 6 validation passed, INDEX verdict matches | Passed with cleanup needed |
| Substantive gate failure, required validator failure, or INDEX/`RESULT:` mismatch | Failed |
| Subset/recheck without full verification, blocked input, missing verdict, timeout, cancellation, or incomplete execution (including `partial`: aborted run with no terminal verdict, CC-09) | Not evaluated as a successful full audit |

Exit status is **not** the oracle: the gate's exit 1 is overloaded (CC-08), so
the literal `RESULT:` line decides; both pass outcomes exit zero. Retain the
literal verdict and exit code. Missing, malformed, or conflicting verdicts are
explicit execution errors.

A validator failure stops dependent work. Route repair through an explicit new
execution attempt, then run a fresh verifier again. Presentation preserves bug
findings even when cleanup or infrastructure issues prevent a clean outcome.

## 7. MCP operation coverage

All tool inputs/results are typed and versioned. Use run-scoped artifact IDs,
not arbitrary read paths. Reject unsupported options and disclose partial
milestone capability; do not silently perform a smaller audit.

| Tool | Responsibility | First usable increment |
|---|---|---|
| `qpb_install` | Run the embedded payload's canonical installer in the authorized run/target layout, preserve backups and attribution, report event output truthfully. | M2/M3 |
| `qpb_validate` | Run deterministic install/layout validation from the embedded payload, return emitted findings and remediation; no cross-checkout repair. | M2/M3 |
| `qpb_run` | Preflight options, persist an accepted job, return `runId` without awaiting the audit, dispatch the MAF workflow. | M3; full parity M8 |
| `qpb_resume` | Reconcile saved evidence, accept scoped operator replies (6.3), validate compatibility, continue the next valid step. | M3/M4 |
| `qpb_recheck` | Start a tracked prior-bug recheck, not a new discovery run. | M8 |
| `qpb_get_status` | Return lifecycle, phase/attempt, iteration, completed steps, pending input, blockers, quality outcome, tool/payload identity. | M3 |
| `qpb_list_artifacts` | Return actual registered artifacts with IDs, kind, size, hash, attempt/iteration, availability. | M3 |
| `qpb_get_artifact` | Read bounded report content by artifact ID, with explicit pagination/truncation and access checks. | M3 |
| `qpb_cancel` | Persist an idempotent cancellation request and expose eventual stop/cleanup status. | M3 |

Keep stdout exclusively MCP protocol traffic. Route host, Python, SDK, and
attribution output to captured evidence/stderr or structured tool results.
Never prompt with `Console.ReadLine` on the MCP transport.

## 8. Implementation increments and gates

Increment IDs are migration milestones, not QPB phase numbers. Every
verification below that touches the filesystem, processes, installation, or a
client runs on **both** Windows and Debian 13 (Trixie) x86-64 unless stated.

### M0 - Freeze the behavioral contract and acceptance baseline

**Depends on:** none. **Status (2026-10-20):** evidence complete; **stop/go gate
met**. Two M0 deliverables stay open and do not block the gate (below).

The original host repository the fork manifest cites does not exist anywhere
that could be found (not on disk, not under the `svolmer` GitHub account). A new
host repository was created at `C:\Sources\CSharp\QualityPlaybook.Agent` and,
per the 2026-10-20 decision, published as the **private** repository
`https://github.com/svolmer/QualityPlaybook.Agent` (head `e77afb9` at the time of
writing). It holds all M0 evidence under `docs/m0/` and the dated decisions in
`docs/decisions.md`; start at `docs/m0/README.md`. A fresh clone with
`--recurse-submodules` reproduces the pin and the payload hash.

**Done:**
- Dependency lock and submodule at `1319df0` (`v1.6.0-maf.2`), fetched by SHA;
  a fresh recursive clone reproduces the pin and the payload hash
  `c24ffd6d140f177911f9eb0afffaae4003cc2fb35d36cdc7ea8114441d9438e9`
  (1365 entries, 37.2 MB, 14.4 MB gzipped, 3 symlinks materialized). The payload
  must be built from `git archive`: a plain Windows checkout with
  `core.symlinks=false` corrupts the skill.
- AI seam inventory: only `bin/run_playbook.py` and
  `bin/skill_derivation/runners.py` launch AI CLIs; classifier and persona seams
  are injected callables; the Council check is plan/assemble; prompts tell the
  agent to run literal `python3` commands.
- Contract map with phase-prompt SHA-256s; contradiction register CC-01..CC-21
  (reconstructed from the fork manifest) plus five new findings.
- Baselines: QPB suite on Windows (Python 3.14.3) and Debian 13 (Python 3.13.5; Debian 12 gave identical results),
  fork versus upstream. Fork test counts reproduce the manifest exactly (3106 and
  3055); the fork adds 51 tests and **no new failing test** on either platform.
  Windows has 45 inherited failures that are real portability defects
  (backslash paths in bundle logic, persona-grounding `hash_mismatch`, cp1252
  decoding of gate output). All Windows failures are classified; 7 more belong
  to the persona grounded-add family.
- Acceptance target: `spectreconsole/spectre.console@bbbb572` (tag `0.57.2`, MIT,
  466 `.cs` files, net8.0/net9.0/net10.0) is fully green on Windows and Debian 13,
  two runs each: `Spectre.Console.Ansi.Tests` 454 and `Spectre.Console.Tests` 747
  passed per framework, no failures or skips.

**Decided 2026-10-20 (details in the host repo's `docs/decisions.md`):**
1. **Live-call and budget policy: staged caps set from measurement.** About 25
   model requests for the M1 spike, on the small fixture `svolmer/Results`, not
   spectre.console. M1 measures a Phase 1 run; caps for M3 onward are about 2x
   that cost and are host-enforced per phase, run, and job, with spend recorded
   as evidence. Models are chosen after M1 lists what the account can use:
   cheapest passing model for ordinary phases, strongest for Phase 3 and the
   Council, which uses three distinct IDs and is budgeted separately.
2. **Remote home:** private repository `svolmer/QualityPlaybook.Agent`.
   **Fork branch:** `compat/v1.6.0-maf` is the line for future fork fixes (new
   commits plus a new tag). It was rebased onto `main`; the **pin is unchanged**
   and is the commit `1319df0`, reachable through the `v1.6.0-maf.2` tag.
3. **Seeded defects:** a synthetic variant of spectre.console `0.57.2` with about
   8-12 defects that leave the existing suite green, delivered as one
   neutral-message commit on a fork branch with the ground truth kept in the host
   repo, plus the clean `0.57.2` as the negative control. Not built; needed
   before M9.

**Still open inside those decisions:** the numeric caps (after M1) and the model
IDs (after M1).

**Carried to M2:** a further fork tag or adapter mitigation for the nested AI
runners, the agent-context refusal, and the Windows defects above.

**Verify:** repeatable source acquisition (Windows symlink handling at build
time), complete import/resource closure, baseline tests and golden fixtures,
dependency/license attribution. Distinguish missing prerequisites from defects.

**Stop/go:** approved immutable pin, complete contract map, selected targets,
explained baseline failures on both OSes. A floating branch or absent corpus
does not pass.

### M1 - Prove the .NET MAF/Copilot execution, permission, and packaging seams

**Depends on:** M0.

**Deliver:** a bounded feasibility spike with exact .NET/MAF/Copilot package and
runtime pins. Create Copilot-backed `AIAgent` instances and execute a real
custom tool through MAF; do not substitute direct SDK-only phase execution.
**Pack the spike as a .NET tool, install it from a local folder feed with
`dotnet tool install --add-source`, and launch it from VS Code Copilot Chat and
from Claude Code over stdio** to surface tool-store, paths-with-spaces, `PATH`,
and read-only-payload problems before later milestones depend on them.

**Verify:**
- Authentication, explicit model selection/availability, reported identity,
  distinct fresh sessions, streaming/results, provider failure surfaces, and
  whether a separately installed Copilot CLI is required and locatable.
- Permission denial for SDK built-ins and approval enforcement for custom
  tools; test the documented pre-tool-hook override hazard.
- No unsolicited repository hooks, instructions, skill loading, or extra MCP
  capabilities in .NET.
- Cancellation, process ownership, stdio disconnect, pending approval, and
  checkpoint/provider-session behavior across a host restart; durable
  checkpoint storage through a custom store, and resume with stable agent IDs.
- A denied tool/unknown model/malformed provider result never becomes success.
- Packaging: portable versus RID-specific decision, package ID/command
  confirmation, `doctor` output, no stdout noise on the transport.
- Confirmation channel (6.3): what each client actually shows the operator, and
  whether a model can invoke the chosen channel.

**Status (2026-10-21): closed.** Evidence is in
the host repo's `docs/m1/README.md`. Established: the RID-specific tool installs and
runs on Windows and Debian 13 (`doctor` exercises payload, installer, utilities and the
Copilot runtime); stdio transport; Claude Code connects; a custom tool runs through a MAF
agent; custom tools and built-in shell are permission-gated; the approval-hook hazard is
real; cancellation, process ownership, checkpoint resume (at-least-once, identity change
refused) and session recovery work. Settled against the plan's assumptions:
- **An unknown model id silently falls back to another model** (observed
  `claude-sonnet-5`), so the host preflights ids against the model list and verifies the
  reported model on every call.
- **Repository instructions and hooks load and run by default**, with no prompt; only a
  hardened session profile (documented in M1 finding 18) prevents it, and a canary-fixture
  test must pin that.
- Cost is token-priced with a large default baseline (about 19,000 input tokens for a
  trivial prompt; about 3,100 hardened), so budgets are measured in tokens.
Later the same day: a pending `RequestPort` request survives a host restart (same id, the run
finishes only once answered), but **MAF accepts a wrong-id or duplicate response without
error and the run then fails**, so the host validates request id, single use and expiry
itself. The out-of-band channel (`qpb-agent confirm`, the only receipt writer, refusing
without a real terminal) is built and tested on Debian 13 and, for the non-terminal steps, on
Windows. It fails closed for model-authored and piped answers but **not for an adversarial
agent running as the operator** (a same-user process can write a receipt file; the test
demonstrates it). That residual risk is the operator's call: accept it, or choose MCP
elicitation or a signed receipt (both untested).
Then verified end to end on Windows with VS Code Copilot Chat as the client: the receipt was
written from a real console, the first resume was accepted with the operator's own answer, and
the second was rejected as already consumed (evidence: the host ledger and the Copilot session
record). Two behaviors shape the design: the model skipped the resume tool twice and misreported
one approval, so a resume must not depend on the model and verdicts come from host evidence; and
VS Code's client-side approvals (including an allow-all switch) never reach the host.
**M1 closed 2026-10-21.** The operator accepted the confirmation channel as built for the first
release (its limit is stated in the install documentation; elicitation and signed receipts are not
required). 23 of the 25-call allowance was used.

Windows prerequisites that M1 measured and the operator accepted: **long paths enabled** (so Python can
read the deepest payload files) and a **tool directory under about 110 characters**, because Windows
refuses to launch a program whose own path is over 259 characters even with long paths enabled
(259 launched, 279 failed; `copilot-runtime.exe` failed at 277-281). The default global location
qualifies. `qpb-agent doctor` checks both, so extracting the payload to a short directory is no longer
a first-release requirement.

**Stop/go:** an exact compatible package set, a tool package that installs and
launches under both clients on both OSes, and demonstrated controls. If model
identity, input isolation, durable approvals, confirmation authenticity, or
cancellation cannot meet the contracts, report the blocker for operator
resolution before expansion.

### M2 - Integrate deterministic Python utilities and controlled tools

**Depends on:** M0 and M1. Deterministic adapter work can start after M0 in
parallel with the provider spike; its live MAF gate requires M1.

**Deliver:**
- A small typed Python adapter running from the embedded payload for canonical
  install, validation, ingestion, citation/assembly, state, `finalize-index`,
  `agents-md`, and artifact operations; preserve their output.
- Controlled repository read/write, patch, and approved build/test tools with
  cancellation, budgets, per-OS path checks and process ownership, and
  execution receipts.
- A MAF execution seam for nested Python AI requests. Prefer existing
  classifier/response and plan/assemble interfaces. Where synchronous
  `LLMRunner.run` cannot consume precomputed responses, implement a narrowly
  scoped request/response adapter to host-dispatched MAF sessions, not AI CLIs.
  Avoid re-entering a suspended caller agent's tool loop.
- Minimal further fork changes (new tag, manifest entry per change, regression
  tests): an explicit MAF-host path for the legacy CLI/environment checks and
  the runner's agent-context refusal, without impersonating an old execution
  mode or disabling artifact enforcement.

**Verify:** direct pinned-Python versus adapter result parity; missing or
too-old Python, the Windows Store alias, malformed events, partial install,
timeouts, cancellation, path/junction/symlink escape, argument injection,
unapproved commands, denied network, read-only payload. Exercise nested
reasoning through MAF and assert no one-shot AI CLI launch.

**Stop/go:** deterministic receipts remain faithful and authoritative; all AI
seams have a demonstrated MAF route or an explicit blocking work item.

**M2 status (2026-10-21): implemented, verified, and published.** Evidence is in
the host repo's `docs/m2/README.md`.
- Typed adapter, controlled repository tools (path guard, budgets, receipts, `git apply` patching, a
  `dotnet restore|build|test` grammar, job-object or process-group ownership), and a mailbox bridge that serves
  the two blocking AI seams (`LLMRunner.run`, persona spawn) from MAF sessions with no AI CLI start attempt.
  The file seams (classification reads, Council plan/assemble) needed no bridge. Live: 4 of the 8 allowed calls.
- **One fork change was needed, not two:** `qpb_validate --host-mode maf` (CC-22, tag `v1.6.0-maf.3`, commit
  `5bf60a1`). The runner's agent-context refusal needed no change because the host never starts the runner.
- The re-pin moves the host to the rebased branch's larger tree (1440 entries, 50.0 MB, +1.0 MB compressed).
- 197 tests pass on Windows and on Debian 13; the full upstream suite has the identical failure set on the
  base and on maf.3.
- **Fork published** by the operator on 2026-10-21 (branch and `v1.6.0-maf.3` on origin; the pinned commit was
  fetched from GitHub by SHA to confirm). Nothing outstanding for M2; M3 may start.

### M3 - Ship the tracked MCP job lifecycle and Phase 1 vertical slice

**Depends on:** M1 and M2.

**Deliver:**
- Stdio host **distributed only as the .NET tool package**, thin command
  handlers, SQLite job state, durable checkpoint storage, target locks,
  pending input, artifact access, and controlled shutdown.
- Install/validate plus a tracked Phase-1-only `qpb_run`, resume/status/
  artifact/cancellation operations. Mark this an explicit subset.
- MAF exploration using original phase instructions, documentation intake,
  classifier reads, role mapping, provenance, and Phase 1 validation.
- Three-lane document authority: structurally validated contracts, disclosed
  unconfirmed prose, and operator-confirmed flagged/self-authority content.
- Install layout and `PYTHONPATH` defined against the real embedded closure;
  do not assume the validator recognizes MAF-only hosts.
- The selected operator-confirmation channel.

**Verify:** `qpb_run` returns a persisted `runId` while a deliberately blocked
phase task remains incomplete; the job is queryable and cancellable. Crash/
restart, lost responses, duplicate resume, genuine operator confirmation (and a
model-authored attempt that must be rejected), conflicting jobs, artifact
traversal, tool-version mismatch on resume, and MCP stdout cleanliness.
Original source is unchanged. All of this runs against the **installed tool**,
not `dotnet run`.

**Stop/go:** a real Phase 1 slice works from VS Code Copilot Chat and Claude
Code on both OSes, resumes truthfully, and preserves validator/provenance
contracts on the selected acceptance target.

**M3 status (2026-10-21): GATE CLOSED by the operator, with waivers (below).** Evidence is in the host repo's
`docs/m3/README.md`.
- Job store (SQLite), lifecycle, leases, target lock, cancellation, artifact access, pending input over the accepted confirmation channel, and
  eight MCP tools plus `qpb_ping` (`qpb_recheck` waits for M8). Phase 1 only, disclosed in every result.
- Verified against the **installed** tool on Windows and Debian 13: persisted `runId` while a blocked task runs, cancel, crash and restart, duplicate
  resume, conflicts, lost response, version mismatch, traversal, stdout cleanliness, source unchanged, and (Debian, real pty) genuine operator
  confirmation with a model-authored attempt rejected.
- A **live** Phase 1 run on the small fixture completed with haiku (16 model calls; 174 across four runs, 400 allowed). Three earlier runs were
  correctly blocked by the real validators, which exposed two prompt-versus-validator contradictions (CC-23, CC-24, not yet in the fork) and
  that the host must render `PROGRESS.md` itself from the run-state log (CC-25).
- Operator decision 2026-10-21: the prompt wording is fixed and the validator stays strict. Fork release `v1.6.0-maf.4` (commit `e8d6d2e`, prose only, with
  a test pinning the prompt against the validator) resolves CC-23 and CC-24; a live run on the maf.4 prompt alone completed. Pushed.
- Claude Code drove the installed tool end to end (headless).
- **Acceptance target (Windows):** Phase 1 completed on spectre.console@bbbb5729 with sonnet-5.5 (16 model calls; 78 of the 1,000 allowed across five
  attempts). Haiku was blocked by the validators and is not adequate on this target. QPB enforces only a ceiling on the role map, and the run's map
  covers 258 of 784 files (33%); the host reports that as an observation. Not run on Debian 13.
- Operator decisions 2026-10-21: role-map coverage stays an observation; the live Debian run on the acceptance target is postponed and not required
  for M3; a target that already tracks `quality/` is audited from a worktree without that folder (implemented in tool `0.1.0-m3.11`, found when the
  Copilot Chat check was pointed at this repository and blocked at Phase 0 with `stale_quality_dir`).
- VS Code Copilot Chat drove the installed tool (m3.10) to a completed Phase 1 job on the small fixture (46 model calls, two repairs; verified from the
  job database, not from Chat's text).
- Operator decision 2026-10-21: the default Phase 1 model is sonnet-5.5 (tool `0.1.0-m3.12`).
- **Gate closed by the operator on 2026-10-21 (repositories pushed), with these waivers:**
  1. The live Debian 13 run on the acceptance target is postponed and not required (stated earlier by the operator).
  2. Neither Claude Code nor VS Code Copilot Chat has driven the tool on Debian 13; the stop/go's "both OSes" clause for the clients is accepted as not met. Debian is covered only by the scripted installed-tool lifecycle (41 checks) and confirmation (13 checks) suites and the unit tests (tool m3.11).
  3. Claude Code drove the tool with the scripted backend, not a live model; the Copilot Chat run used haiku-5.5 on the small fixture, on tool m3.10, and needed two repairs.
  4. Role-map coverage is an observation, not enforced (33% on spectre.console).
  5. On the acceptance target one completion (sonnet-5.5, Windows) is the evidence; it is not a success rate. The Debian checks ran on m3.11, before the default-model change to m3.12.

### M4 - Preserve Phase 2 generation, human validation, and personas

**Depends on:** M3.

**Deliver:** MAF generation with original requirements/tests/review protocols;
manifest/render contracts, RUN_CONTRACT separation, traceability, coverage/gaps,
requirements interview, append-only confirmations **with the host receipt
cross-check (CC-19)**, and isolated persona remediation. Reuse deterministic
grounding/merge/renumber helpers.

**Verify:** golden schema/contract fixtures and mutation failures; unchanged
record/citation attachment except explicitly permitted changes; human answers
round-trip into citable transcripts; confirmations survive re-derivation; a
forged `operator-confirmation` ledger line without a receipt fails the run.
Test persona source/secret/network denial, poisoning, candidate-only ungrounded
adds, conflict handling, and `agent-validation` versus human provenance.

**Stop/go:** Phase 2's required artifact set and validator pass; no
manufactured human confirmation or source-fed persona. Static golden files do
not prove live prompt fidelity: perform live generation checks.

**M4 status (2026-10-22): implemented and verified; awaiting the operator's decision to close, with three live limits stated.** Evidence is in the host
repo's `docs/m4/README.md`.
- `qpb_run through=2` generates Phase 2 with the original prompt through MAF, under a writable-artifact policy; the host runs the validators the prompt asks the
  agent to run (phase-boundary, run-state contract, the gate's render-contract / ledger / functional-test / review checks, the mechanical verifier). CC-19 is closed
  by host receipts for every ledger line and a cross-check that fails the run on a forged, altered, reordered or removed line, or on provenance no receipt accounts for.
  The interview is the operator's own terminal command; the expert review runs QPB's `run_feature_h` through the embedded driver with isolated one-tool reviewer sessions,
  host-computed citation excerpts, a receipt, a re-render the agent cannot use to change the manifest, the disclosure, and an undo.
- Live (sonnet-5.5, 389 of 600 allowed calls): Phase 1 and 2 completed on `Results` (several runs) and on **spectre.console@bbbb5729** (81 calls, 815 s; 12 product
  requirements, all references resolve, two spot-checked claims accurate; 8 reviewer confirmations applied, 25 candidates held for the operator, no conflicts).
- Live runs found two defects the unit tests could not: a model reads the guide and skips the templates it points to (fixed in the host notes; protocols 2 to 3 times
  longer), and on a Windows checkout every reviewer citation failed `hash_mismatch` because QPB's ingest and citation verifier hash different bytes for CRLF documents
  (the host now checks the audited commit out as committed; verified offline with tests that fail without the fix, **not re-run live**).
- Tests, tool `0.1.0-m4.8`: 221 AgentRuntime and 162 Orchestration on Debian 13; 50 installed lifecycle checks on Windows and Debian; 13 confirmation and 18 interview
  checks (real pty) on Debian.
- **Live grounded reviewer add observed (2026-10-22, 454 of 600 calls):** with a citable contract document the reviewers' backed changes were applied (8 additions, 1 correction,
  host-computed byte-verified excerpts, Tier 1), re-rendered and the job completed. It also showed two QPB defects: reviewers duplicate each other and the merge keys on exact
  text (eight near-identical additions from four reviewers), and a grounded `correct` leaves a Tier 3 record carrying a citation, which QPB's own Phase 6 gate rejects (a fork
  change like CC-26 would set the tier from the cited document, as the add path does).
- **Generated tests compiled and run (2026-10-22):** the seven live `test_functional.cs` files were run in the targets' own test projects. Six compile; the spectre.console one builds in the
  repository's own test project (54 tests, 31 pass, 23 fail on real divergences from the requirements, none a setup error); one Results file does not compile (it uses the library's `internal`
  members), which no validator in QPB or the host detects. The model also wrote four different kinds of functional test from the same prompt (fail-on-defect, skip-the-defect,
  pin-today's-behaviour, non-compiling).
- **Host compile check built (required by the operator, tool `0.1.0-m4.9`):** a C# functional test is built inside the target's own test project in a separate checkout (policy-checked
  `dotnet restore`/`build`), a Python one is parsed; errors go back to the agent, a target with nothing to compile it with or a check that cannot be made is reported and never counted as a pass.
  Replayed with the scripted backend over the saved live artifacts: run F's real file fails with its 15 errors and the repair compiles; spectre.console's real file builds in
  `src/Spectre.Console.Tests`. 221 AgentRuntime and 176 Orchestration tests on Debian 13; 50 installed lifecycle checks on both OSes.
- **Open for the operator:** close M4 with (1) the agent turn applying an interview correction, addition or drop tested only with a scripted agent, no operator having run an interview
  against a live generation; (2) the two QPB defects above, with or without a fork release first; (3) the model's varying idea of a functional test (fail on the defect, skip it, pin today's behaviour).

### M5 - Preserve Phase 3 three-pass review and derivation/divergence

**Depends on:** M4.

**Deliver:** the original three-pass review protocol, confirmed-bug writeups,
regression patches, and applicable skill-as-code derivation/divergence
behavior. Route every nested model request through the M2 seam.

**Verify:** language-appropriate review fixtures and known-defect/negative
controls; complete traceability and real regression tests, not stubs. Instrument
process launches to prove Python derivation cannot fall back to Claude/Copilot/
Codex/Cursor phase CLIs.

**Stop/go:** required review artifacts and prerequisites pass for Code/Skill
roles as applicable. Unsupported required nested reasoning blocks the run.

### M6 - Preserve Phase 4 independent Council and citation review

**Depends on:** M5.

**Deliver:** three explicitly assigned, mutually blind MAF auditors; original
audit/triage/probe contracts; net-new regression tests; same-roster Layer-2
semantic citation review using existing deterministic prompt/assembly helpers.
Bind Python Council assembly to the recorded run roster without altering the
operator's global QPB configuration or using QPB's default roster.

**Verify:** distinct effective model/session identities; no peer conclusions in
initial inputs; missing/duplicate/replaced model failures (host-enforced size
and distinctness); majority overreach handling; malformed/incomplete responses;
stable reviewer IDs across spec audit and citation review; approved
roster-change invalidation.

**Stop/go:** all three configured reviewers ran with verifiable assignments and
valid outputs. Unavailable independence blocks the stage; three instances of
one model or a two-member audit never pass it.

### M7 - Preserve Phase 5 TDD and Phase 6 authoritative verification

**Depends on:** M6.

**Deliver:**
- Reconciliation of every finding, completeness reporting, runner probes,
  actual red/green test execution, exemptions, patch receipts, and cleanup.
- Host-run gate, `finalize-index`, `agents-md`, and phase validator with
  literal process evidence, then a separately created fresh-context MAF
  verifier using the original audit instructions. Map all three gate outcomes
  using the section 6.4 contract.
- Final INDEX/progress/report contracts and host-controlled artifact
  publication. The verifier never repairs failures.
- Group-context support with mandatory independent Council/Phase 6 sessions.

**Verify:** real failing regression on unpatched code and passing regression
with a valid fix; unavailable runners; denied dependency restoration; failed
patch apply/reverse; interrupted verification; preserved original source.
Mutate gate/validator outputs and the INDEX verdict to prove an agent's PASS
narrative cannot override failure, missing execution, a verdict mismatch, or a
cleanup-needed verdict.

**Stop/go:** successful, cleanup-needed, and substantive-failure fixtures map
correctly. Final success requires all authoritative checks, not exit zero alone.

### M8 - Complete execution-option parity, iterations, and recheck

**Depends on:** M7.

**Deliver:**
- Full run: phases 1-6 followed by gap, unfiltered, parity, and adversarial
  (the QPB meaning of "run the Quality Playbook"). Also explicit valid phase
  subsets/groups and ordered iteration selections.
- Shared context for requested working-phase groups where valid; disclose
  Phase 6's forced fresh-context split; retain per-phase gates.
- Native iterations using `iteration_prompt` text, hash-pinned against the
  embedded payload (CC-16); numbered/merged exploration, demoted candidates,
  cumulative traceability, renewed phases 2-6/TDD. Never clear the quality
  tree because another iteration starts. Iterations require the precondition
  `GATE PASSED` or `PASSED WITH CLEANUP NEEDED` plus
  `VALIDATION PASSED (phase 6)`.
- `qpb_recheck`: inspect only previously reported bugs, use the existing
  patch/test workflow, emit recheck schema 1.0 results and summary with
  `FIXED`, `PARTIALLY_FIXED`, `STILL_OPEN`, or `INCONCLUSIVE`, with the
  per-status tally equal to the summary counts (enforced by the fork's gate,
  CC-17). No new-bug discovery.
- Phase 7 presentation/drill-down and improvement choices via MCP artifacts and
  status, without applying fixes to the original source; return the AGENTS.md
  adoption patch alongside the reports.

**Verify:** option/dependency matrix, malformed plans, missing prerequisite
artifacts, grouped context and restart, all four strategy contracts, real TDD
for new iteration findings, recheck status fixtures, cancellation cleanup. Do
not require identical stochastic prose or bug counts.

**Stop/go:** all nine MCP operations and the full behavioral matrix are
implemented; subset/recheck results cannot be mistaken for a full verified run.

### M9 - Acceptance, tool-package release, and operational handoff

**Depends on:** M8.

**Deliver:** documented VS Code and Claude Code configuration, exact
dependency/package locks, Python/Copilot prerequisite checks (`qpb-agent
doctor`), architecture/interaction/safety documentation, attribution/licenses,
and the released **.NET tool package(s)** on the operator-approved feed with
every package of the set pushed together. The complete pinned dependency is
embedded reproducibly; nothing is fetched during a quality run.

**Verify:**
- Host unit/contract tests, deterministic Python compatibility tests, and
  actual MCP transport tests with a fake long-running workflow, on both OSes.
- **Fresh machine of each OS: `dotnet tool install` of the exact released
  version from the feed, `doctor` passes, both clients launch it; `dotnet tool
  update` and `uninstall` leave job state intact; a job interrupted on version
  N blocks with `incompatible_host` on N+1 and resumes after reinstalling N.**
- End-to-end live runs on the spectre.console acceptance target:
  methodology/artifact contracts, independent Council receipts, seeded-defect
  detection and negative controls, genuine TDD, final outcome mapping,
  worktree-only edits, and all iteration/recheck operations.
- Fault injection at tool, phase, checkpoint, publication, and shutdown
  boundaries; restart without duplicate side effects or false completion.
- Paths with spaces, required symlink handling, permissions, and stdio EOF.
- Operator-approved cleanup/retention; no credentials in reports or
  distributable logs, no generic shell MCP tool, and no unapproved legacy AI
  executor.

**Stop/go:** no unexplained migration regressions relative to M0; all required
positive/negative/fault controls pass on both OSes; real validator evidence
supports the outcome. Benchmarks that could not execute are disclosed blockers,
not waived by a structural test suite.

## 9. Dependency order and scope limits

```text
M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9
 |          ^
 +----------+  deterministic M2 work may begin before M1 completes
```

The first usable increment is a clearly labeled Phase 1 subset delivered as an
installable tool, not a "completed Quality Playbook migration." Full-release
acceptance is M9.

No cloud hosting, HTTP transport, provider-neutral agent framework, detached
worker, multi-job scheduler, automatic original-source fix application, OS
sandbox, self-updating, non-`dotnet tool` install channel, macOS,
Linux other than Debian 13 on x86-64, or Visual Studio (full IDE) support is included in the
first release. Add any of these only after a new operator decision and a
demonstrated need. No schedule, cost, model roster, or arbitrary performance
threshold is invented by this plan.

## Appendix A - Consolidation log

| # | Finding | Resolution in this revision |
|---|---|---|
| 1 | Plan said no compatibility fork existed. Tags `v1.6.0-maf.1`/`.2` exist locally and on `origin`. | Sections 1, 2, 3, M0 updated; pin is commit `1319df0`. |
| 2 | "Known contract conflict" (INDEX never adopted; `pass-with-cleanup` missing) is real on `main` but resolved in the fork (CC-05, CC-02/03). | Section 3 conflict table; section 6.4 states the contract. |
| 3 | Pin ambiguity: v1.6.0 (`400f66f`) versus the fork, and `main` (`1001b38`) versus both. | Pin by commit; `main` is navigation only. |
| 4 | Fork keeps version `1.6.0` (deliberately breaks the AGENTS.md bump rule). | Identity recorded by commit/tag plus lock `compatibilityFork`. |
| 5 | Installation was an unassigned "distribution format" and the plan assumed a Git submodule. Requirement: dotnet tool. A submodule is not present on an installed machine. | New section 5; submodule is build-time only; tool embeds `git archive` payload; M1, M3, M9 gates changed. |
| 6 | `dotnet tool update` reinstalls the latest, which conflicts with "never auto-upgrade interrupted runs." | Operator-only updates; `incompatible_host` block; tool-path side-by-side; feed retention (5.4). |
| 7 | pip channel (`import bin` must fail) cannot serve the host's `python -m bin.*` calls. | pip and clone copies declared unsupported (5.2). |
| 8 | QPB ships a default Council roster; plan says "no host default." | Host always passes an explicit roster and ignores QPB defaults (2, 6.3, M6). |
| 9 | Code accepts any non-empty roster (CC-18); the plan assumed enforcement. | Host enforces three distinct IDs. |
| 10 | Gate exit code treated as sufficient; exit 1 is overloaded (CC-08); witness is last `RESULT:` line plus `Total:` (CC-04); INDEX verdict must match (CC-03). | Section 6.4 rewritten. |
| 11 | Phase 6 finalization had no owner. | Host runs `finalize-index` and `agents-md` before the fresh verifier (6.4, M7). |
| 12 | Residual risk: forged `operator-confirmation` lines pass the gate (CC-19). | Host receipt cross-check in 5.4, 6.3, M4. |
| 13 | Plan treated `run_playbook` iteration as reference only; fork (CC-16) says host runs iterations with its prompt text. | M8 hash-pins that text. |
| 14 | Bare `python3` on the Windows host is the install-manager alias and times out. | Absolute interpreter resolution per OS (5.3, M2). |
| 15 | Compile-cache writes can false-fail validation (AGENTS.md 090q). The tool store is read-only. | `PYTHONDONTWRITEBYTECODE`/cache prefix; no `-I` (5.3). |
| 16 | MAF resume requires stable topology and executor/agent IDs; checkpoint stores are a trust boundary. | Workflow fingerprint in state; protected storage (5.4, 6.2). |
| 17 | The .NET page documents only in-memory checkpoints. | Durable store is explicit host work (M1, M3). |
| 18 | Python docs say workspace hooks are off by default; that is not claimed for .NET. | M1 proves .NET repo-hook/skill isolation (6.1). |
| 19 | Fork lists no change for nested AI runners or the agent-context refusal. | Assigned to M2 with a further fork tag. |
| 20 | Fork branch `compat/v1.6.0-maf` is not on `origin`. | M0 operator decision; pin by commit. |
| 21 | The 148-test run is a `main` subset. | Superseded by fork full-suite baselines. |
| 22 | The host repo (`docs/m0/...`, lock file) is not in this workspace. | Stated plainly; M0 re-verification item. |
| 23 | AGENTS.md install step 7 requires showing the attribution banner. | Returned in `qpb_install` result and stderr (5.3). |
| 24 | **Operator edit during this review:** platform became Windows and Debian-based Linux with VS Code Copilot Chat and Claude Code (was Windows-only, Visual Studio 2026). The draft's Windows-only and Visual Studio statements conflicted with it. | Adopted as authoritative; sections 1, 2, 5, 6.1, 8, 9 made cross-OS; Visual Studio moved out of scope. |
| 25 | The fork's only recorded baseline is Windows. | Debian baseline added to M0. |
| 26 | Debian-based distributions can ship Python older than the core's `>=3.10`. | Preflight rejects with remediation (5.3). |
| 27 | VS Code and Claude Code use different MCP config keys (`servers` vs `mcpServers`). | Both shown in 5.2. |
| 28 | Both clients let a model call `qpb_resume`; Claude Code can run MCP tools without prompts in non-interactive/bypass modes. This can make an agent-authored answer look like operator confirmation. | New requirement and candidate channels in 6.3; verified in M1/M3; client approval not relied on (6.1). Needs an operator choice. |
| 29 | Client-side `PATH` may lack the tools directory (GUI-launched editors). | `doctor` reports resolved path; absolute-path fallback (5.2). |
| 30 | `autocrlf` could change payload bytes if built from a working tree. | Payload built from the commit on one CI OS (5.3). |
| 31 | **Operator decision:** the acceptance target is spectre.console and no non-.NET target is required. Earlier candidates (`svolmer/Results`, `encode/httpx`) were dropped. | Section 2 row, M0, M3, M9 updated; C#-only coverage disclosed. |
| 32 | **Operator decisions (2026-10-20):** staged budget policy, private remote home, published fork branch, and the synthetic seeded-defect approach. Confirmed command allowlist for the target. | Section 8 M0 and the host repo's `docs/decisions.md`. |
| 33 | The operator rebased `compat/v1.6.0-maf` onto `main`; the rebase duplicated this plan inside the fork (a 1,578-line file with two copies) and folded it into the maf.2 commit. | Runtime paths verified byte-identical to the pin; the pin stays `1319df0`. The plan lives on `main`, not in the fork; the fork manifest records the rebase. |

## Appendix B - Verification coverage

**Verified in this pass (repository):** every file linked in the first revision
exists; `main` HEAD and tag commits; fork tags on `origin`; the fork manifest;
INDEX/`pass-with-cleanup` behavior in `validate_phase_artifacts.py`,
`schemas.md`, `run_state_schema.md`, and `phase6_auditor.md` on `main`; the
148-test figures; v1.6.0 design section headings; runner phase/iteration flags;
pip packaging constraint; Council default roster presence.

**Verified in this pass (official docs, 2026-10-20):** the Copilot agent,
workflow checkpoint, C# MCP server/NuGet, and .NET tools pages; the Claude Code
MCP page (first 100,000 of about 123,000 characters); a summary of the VS Code
MCP page.

**Not verified (carry into M0/M1):** the host repo's lock file and baselines;
whether `Microsoft.Agents.AI.GitHub.Copilot` is prerelease at the chosen
version; .NET model-selection API and Copilot CLI prerequisite details on each
OS; the `.csproj` properties generated for a tool with the `McpServer` package
type; VS Code's exact `mcp.json` reference, its elicitation support, and its
current preferred configuration location; Claude Code's permission-rule
behavior for MCP tools and the unread elicitation details; the GitHub-docs
Copilot SDK integration page; feed package-size limits. Nothing in this plan should be read as proof that the
chosen package set works together.
