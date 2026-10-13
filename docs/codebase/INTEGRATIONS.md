# External Integrations

Evidence snapshot: 2026-10-13, HEAD `746bfeb`. Integration implementations were
inspected without making live AI, registry, publish, or credential requests.

## Core Sections (Required)

### 1) Integration Inventory

Criticality is scoped to the operation needing the integration, not a measured
availability/SLO classification.

| System | Type | Purpose | Auth model | Criticality | Evidence |
|--------|------|---------|------------|-------------|----------|
| Claude CLI | External process/provider transport | Execute prompts and audits | Delegated to installed CLI; [TODO] current host authentication not verified | High for Claude-selected runs | [adapters](../../bin/skill_derivation/runners.py), [batch runner](../../bin/run_playbook.py) |
| Copilot / legacy gh copilot | External process/provider transport | Default batch runner; multi-model reviews | Delegated to CLI/GitHub setup; resolver prefers standalone Copilot | High for Copilot-selected runs | [resolver](../../bin/copilot_resolver.py), [runner](../../bin/run_playbook.py) |
| Codex and Cursor CLIs | External processes/provider transports | Alternative prompt execution | Delegated to installed CLIs; [TODO] host accounts/models not verified | High for selected runs | [adapters](../../bin/skill_derivation/runners.py) |
| Git / GitHub gh | VCS + remote API through CLI | History, repository operations, awesome-copilot submission | `gh auth status` preflight for submissions; Git remote auth is external | High for submission; not required by every pure helper | [submission script](../../bin/submit_awesome_copilot.py) |
| PyPI / TestPyPI | Package registry; HTTPS JSON verification | Publish and verify Python distribution | Manual publisher uses Twine credentials; workflow uses OIDC trusted publishing | High for pip releases only | [publisher](../../bin/publish_pip.py), [workflow](../../.github/workflows/publish.yml) |
| npm registry | Package registry through npm | Package/publish Node transport plus Python bundle | Manual publisher checks `npm whoami`; workflow uses OIDC permissions/provenance | High for npm releases only | [publisher](../../bin/publish_npm.py), [workflow](../../.github/workflows/publish.yml) |
| Claude plugin marketplace | Git-backed catalog | Skill distribution/discovery | Host tooling handles access | High for marketplace installs only | [catalog](../../.claude-plugin/marketplace.json), [README](../../README.md) |
| Mermaid CLI (`mmdc`) | Optional local renderer | Render calibration relationship graphs | No auth is shown for local rendering | Optional | [visualizer](../../bin/visualize_calibration.py) |

No direct vendor HTTP SDK is declared in the core package manifests. Most AI
transport is through subprocess CLIs. The reviewed pip publisher also performs
an HTTPS request to `https://pypi.org/pypi/quality-playbook/json` for verification.

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| Target `quality/` JSON/Markdown/patch files | Requirements, findings, tests, review receipts, manifests | Agent procedure and plugin helpers | Cross-artifact consistency and truthful execution receipts | [schemas](../../schemas.md), [gate](../../plugins/quality-playbook/skills/quality-playbook/scripts/quality_gate.py) |
| `quality/logs/<run-id>/` and run-state JSONL | Transcripts, events, progress, resume evidence | Runner and state library | Full prompt retention and incomplete records | [runner](../../bin/run_playbook.py), [state](../../plugins/quality-playbook/skills/quality-playbook/scripts/run_state_lib.py) |
| `reference_docs/` | Intake text, operator citation decisions | Ingest and classifier | Untrusted content must not self-authorize | [ingest](../../plugins/quality-playbook/skills/quality-playbook/scripts/reference_docs_ingest.py), [classifier](../../plugins/quality-playbook/skills/quality-playbook/scripts/doc_classification.py) |
| User `.qpb/config.json` / XDG alternative | Runner/Council overrides | JSON persistence with atomic replace | Invalid config may warn and revert to defaults | [config](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_config.py), [Council](../../plugins/quality-playbook/skills/quality-playbook/scripts/council_config.py) |
| Harness run directories | Pool status, queue/results, heartbeat files | Idempotent tick engine | Missing/late/malformed worker heartbeat | [tick engine](../../bin/qpb_harness_tick.py) |

The reviewed manifests and runtime paths show filesystem-backed persistence, not
an application database, cache service, gateway, service mesh, or message broker.
[TODO] Private deployment integrations outside this repository are unknown.

### 3) Secrets and Credentials Handling

- QPB delegates AI authentication to host CLIs; no operator credential values
  were read during mapping.
- The manual pip publisher checks user `.pypirc` availability or
  `TWINE_USERNAME`, `TWINE_PASSWORD`, and optionally `TWINE_REPOSITORY_URL`.
  This documents variable names only, not contents.
- The manual npm publisher checks `npm whoami`; the submission path checks
  `gh auth status`.
- The release workflow grants `id-token: write` in registry publishing jobs and
  uses a `release` environment. [TODO] Remote environment approvals and actual
  trusted-publisher registrations were not verified.
- The inspected integration wrappers contain credential lookups and public
  service identifiers, not an identified literal credential. This was not an
  exhaustive secret scan.
- [TODO] Credential rotation, token lifetime, and global log-redaction policies
  are not established by the reviewed repository files.

### 4) Reliability and Failure Behavior

- Derivation adapters default to 600-second subprocess timeouts and capture
  timeout failures as return code 124. This does not imply a timeout on every
  external operation.
- Batch `run_prompt` records subprocess exit codes and a missing-command error;
  the reviewed invocation has no explicit timeout. Other runner probes/gate
  calls have operation-specific limits.
- The Copilot resolver caches CLI detection for one process, prefers standalone
  Copilot, probes the legacy extension if needed, and otherwise raises actionable
  `CopilotCLIUnavailable`.
- The pip publisher verifies via `pip index versions`, then a JSON API fallback
  with a 20-second HTTPS timeout. It reports verification failure explicitly.
- Runner pacing and harness pool limits/cadence bound scheduling, not universal
  provider retries. [TODO] No uniform circuit breaker or shared exponential
  backoff policy was found across reviewed integrations.
- Gate callers must read the result category, not only exit code: cleanup-needed
  and a completely clean pass both return zero.

### 5) Observability for Integrations

- [run_playbook.py](../../bin/run_playbook.py) records exact command, prompt,
  working directory, combined output transcript, and exit status.
- [RunnerResult](../../bin/skill_derivation/runners.py) exposes elapsed
  milliseconds, stdout, stderr, and return code.
- Run-state JSONL and heartbeat fields provide workflow progress; harness tables
  show state and worker activity.
- [TODO] No centralized APM/OpenTelemetry/exported metrics backend was identified
  in the reviewed integration/config surface. Local files are the observed
  telemetry substrate.
- [TODO] Provider request-level latency, usage accounting, and live model
  availability were not measured here.

### 6) Evidence

- [bin/skill_derivation/runners.py](../../bin/skill_derivation/runners.py)
- [bin/copilot_resolver.py](../../bin/copilot_resolver.py)
- [bin/run_playbook.py](../../bin/run_playbook.py)
- [bin/publish_pip.py](../../bin/publish_pip.py)
- [bin/publish_npm.py](../../bin/publish_npm.py)
- [bin/submit_awesome_copilot.py](../../bin/submit_awesome_copilot.py)
- [.github/workflows/publish.yml](../../.github/workflows/publish.yml)
- [qpb_config.py](../../plugins/quality-playbook/skills/quality-playbook/scripts/qpb_config.py)
