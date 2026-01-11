Acknowledged. Plan: define Phase 6.1 Control Plane as governance schemas, policy resolution, execution binding, and invariants; mark immutable; stop.

---

## Phase 6.1 — Control Plane (Governance Layer)

### 1) Control Plane Schemas

**Organization**
- `id` (UUID, required)
- `name` (string, required, max 255 chars)
- `slug` (string, required, unique, lowercase alphanumeric + hyphens)
- `created_at` (timestamp, required)
- `version` (int, required, starts at 1)
- `parent_version_id` (UUID|null)
- `status` (enum: ACTIVE|ARCHIVED, default ACTIVE)
- `immutable` (bool, false until archived; archived orgs are immutable)
- Governance: `owner_id` (string), `policy_version_id` (UUID, reference to default Policy)
- Audit: `actor`, `actor_role` (enum: Admin|Owner), `timestamp`

**Project**
- `id` (UUID, required)
- `org_id` (UUID, required, foreign key to Organization)
- `name` (string, required, max 255 chars)
- `slug` (string, required, unique per org)
- `created_at` (timestamp, required)
- `version` (int, required, starts at 1)
- `parent_version_id` (UUID|null)
- `status` (enum: ACTIVE|ARCHIVED, default ACTIVE)
- `immutable` (bool, false until archived)
- Governance: `owner_id` (string), `policy_version_id` (UUID, reference to Policy; inherits from org if null)
- Audit: `actor`, `actor_role` (enum: Admin|Owner|ProjectLead), `timestamp`

**Repository**
- `id` (UUID, required)
- `repo_id` (string, required, external stable identifier, must match Phase 1 `repo_id`)
- `project_id` (UUID, required, foreign key to Project)
- `org_id` (UUID, required, denormalized for fast lookup)
- `name` (string, required)
- `url` (string, required, e.g., `https://github.com/org/repo`)
- `created_at` (timestamp, required)
- `version` (int, required, starts at 1)
- `parent_version_id` (UUID|null)
- `status` (enum: ACTIVE|ARCHIVED|SUSPENDED, default ACTIVE)
- `immutable` (bool, false until archived/suspended)
- Governance: `default_environment` (enum: DEV|STAGING|PROD), `policy_version_id` (UUID; inherits if null), `approval_required_for_prod` (bool)
- Audit: `actor`, `actor_role`, `timestamp`

**Environment**
- `id` (UUID, required)
- `repo_id` (UUID, required, foreign key to Repository)
- `org_id`, `project_id` (denormalized)
- `name` (enum: DEV|STAGING|PROD, required)
- `created_at` (timestamp, required)
- `version` (int, required, starts at 1)
- `parent_version_id` (UUID|null)
- `status` (enum: ACTIVE|DISABLED, default ACTIVE)
- `immutable` (bool, false until disabled)
- Governance: `policy_version_id` (UUID, specific to this environment), `approval_gate` (bool, if PROD then true by default), `notification_targets` (array<email|slack_channel>)
- Audit: `actor`, `actor_role` (enum: Admin|EnvOwner), `timestamp`

**Policy**
- `id` (UUID, required)
- `org_id` (UUID, required, foreign key to Organization; policies are org-scoped)
- `version` (int, required, starts at 1)
- `parent_policy_id` (UUID|null, links to prior version)
- `created_at` (timestamp, required)
- `status` (enum: DRAFT|ACTIVE|SUPERSEDED|ARCHIVED, default DRAFT)
- `immutable` (bool, true if status ≠ DRAFT)
- `scope` (enum: ORG|PROJECT|REPO|ENVIRONMENT, required)
- `description` (string, required, max 1000 chars)
- `policy_rules_ids` (array<UUID>, references to PolicyRules records)
- `effective_date` (timestamp, required)
- `expires_at` (timestamp|null, if set, policy auto-expires and parent or default applies)
- Audit: `authored_by` (actor), `approved_by` (actor|null, required if status=ACTIVE), `timestamp`

**PolicyRules** (append-only, immutable)
- `id` (UUID, required)
- `policy_id` (UUID, required, foreign key to Policy)
- `org_id` (UUID, required)
- `created_at` (timestamp, required)
- `version` (int, required, starts at 1)
- `immutable` (bool, always true)
- Rule definitions (one per record):
  - `safety_class_required` (enum: SAFE|NEEDS_REVIEW|SUGGESTION, required) — min safety for auto-fix
  - `simulation_gate_policy_version_id` (string, required) — which Phase 3 policy gates the simulation
  - `requires_human_approval` (bool, default false) — for all runs or conditional per safety class
  - `approval_roles_required` (array<enum: Admin|ProjectLead|SecurityLead|EnvOwner>, required if approval_required=true)
  - `max_blast_radius_percent` (float 0–100, default 50) — Phase 3 constraint; if exceeded, escalate
  - `allowed_environments` (array<enum: DEV|STAGING|PROD>, required) — where fixes can auto-apply
  - `auto_pr_enabled` (bool, default false) — may create PRs automatically
  - `rollback_slo_minutes` (int, required) — max time to rollback if something goes wrong
  - `audit_retention_days` (int, required, default 365) — how long to retain decision records
  - `notification_on` (array<enum: APPLIED|ROLLED_BACK|FAILED|REQUIRES_REVIEW>, required)
- Audit: `rule_author` (actor), `rule_approver` (actor|null), `timestamp`

---

### 2) Policy Resolution Contract

**Resolution Order (Deterministic Hierarchy)**
1. Environment-specific Policy (if exists and ACTIVE)
2. Repository-specific Policy (if exists and ACTIVE)
3. Project-specific Policy (if exists and ACTIVE)
4. Organization default Policy (must exist and be ACTIVE)
5. **System Default Policy** (immutable fallback; never null)

**Inheritance Rules**
- A lower-scoped Policy is not "inherited" but rather overrides only its own rules.
- Explicit null in a field means "use parent scope's value"; explicit non-null means "override".
- Example: Repo policy can override `requires_human_approval` but inherit `simulation_gate_policy_version_id` from Project.

**Conflict Resolution**
- If two or more policies at the same scope are ACTIVE for overlapping `effective_date` ranges, return error; no ambiguity allowed.
- If a Policy SUPERSEDED or ARCHIVED during a run, the run continues with the frozen Policy (see Execution Binding Contract).
- If a Policy expires (`expires_at` reached) and no parent/fallback exists, system denies new runs for that scope; escalate to Admin.

**Default Fallback Behavior**
- System Default Policy (hardcoded, immutable):
  - `safety_class_required` = SAFE
  - `requires_human_approval` = false
  - `allowed_environments` = [DEV]
  - `auto_pr_enabled` = false
  - `max_blast_radius_percent` = 25
  - `rollback_slo_minutes` = 60

**Deterministic Resolution Query**
- `{org_id, project_id?, repo_id?, environment_name?} -> resolved_policy_rules` with audit trail showing which scope(s) applied.

---

### 3) Execution Binding Contract

**Policy Binding to Run**
- When a run_id is created (Phase 1), the Control Plane resolves the applicable Policy at that moment.
- A new record, **RunPolicy**, is written (immutable, append-only):
  - `id` (UUID)
  - `run_id` (string, from Phase 1)
  - `repo_id` (string, from Phase 1)
  - `org_id`, `project_id` (from Repository metadata)
  - `environment_name` (enum, from Repository or run input)
  - `policy_id` (UUID, the resolved Policy)
  - `policy_version` (int, the resolved Policy's version)
  - `resolved_rules` (snapshot of all PolicyRules at resolution time)
  - `resolved_at` (timestamp)
  - `created_at` (timestamp)
  - `immutable` (bool, always true)
  - Audit: `resolved_by` (actor/system), `resolution_rationale` (string)

**Frozen Metadata Per Run**
- After RunPolicy is written, the following are frozen for the lifetime of that run:
  - `safety_class_required`
  - `simulation_gate_policy_version_id`
  - `requires_human_approval`
  - `approval_roles_required`
  - `max_blast_radius_percent`
  - `allowed_environments`
- Any Phase 2 consensus, Phase 3 simulation, or Phase 5 EDR must reference and respect the frozen RunPolicy.

**Integration with Phase 3 Simulation**
- SimulationRequest (Phase 3) must include `run_id`.
- Phase 3 simulation gate resolves `policy_version_id` from RunPolicy.
- Pass/fail thresholds are determined by frozen `simulation_gate_policy_version_id`.

**Integration with Phase 5 EDR**
- Engineering Decision Report (Phase 5) must reference `run_id`.
- EDR includes a link to RunPolicy (`run_policy_id`).
- EDR approval rules (mandatory signers) are drawn from `approval_roles_required` in RunPolicy.

---

### 4) Governance Invariants

**Engine Remains Stateless**
- The execution engine (Ruff, ESLint, AI, Phase 2 agents, Phase 3 simulator) has zero dependencies on Control Plane state.
- Control Plane is a read-only advisory layer for pre-execution gating only.

**Control Plane Never Edits Code**
- No agent, policy, or component in Control Plane writes to, modifies, or deletes user code.
- Control Plane enforces guards; the engine executes fixes.

**All Enforcement is Pre-Execution**
- Policy gates are evaluated before `run_id` is created (or at creation time).
- If a Policy gate fails, the run is rejected with explicit reason; no partial/degraded execution.
- No policy can retroactively modify a run after RunPolicy is frozen.

**Full Auditability**
- Every Control Plane change (Org, Project, Policy, Environment, RunPolicy) is immutable and queryable by date/actor/scope.
- Every run links to its RunPolicy, which links to the Policy(ies) and rule snapshots in effect.
- Compliance audits can fully reconstruct governance state at any historical point.

**Deterministic Behavior**
- Policy resolution for the same (org_id, project_id, repo_id, environment, timestamp) always yields identical results.
- RunPolicy snapshots are idempotent; re-resolving a historical run's policy from archived records produces the same frozen state.
- No probabilistic or heuristic evaluation in policy resolution.

**Backward Compatibility**
- Existing CLI (e.g., `python3 agi_engineer_v3.py <repo> --smart --pr`) continues to work.
- If no Control Plane Policy is registered for a repo, system applies System Default Policy.
- Dashboard and API remain unchanged; Control Plane is an optional overlay.

**No Implicit Side Effects**
- A Policy change does not retroactively affect existing runs or EDRs.
- A Policy expiry does not delete historical records; it only blocks new runs under that Policy.
- An Organization/Project/Repository archival does not delete Phase 1 memory or Phase 5 EDRs; records remain queryable.

---

### 5) Operational Guarantees

**Policy Lifecycle Transitions**
- DRAFT → ACTIVE (requires approval; immutable thereafter)
- ACTIVE → SUPERSEDED (new version created; old version marked SUPERSEDED; both remain queryable)
- SUPERSEDED or ACTIVE → ARCHIVED (final state; immutable)

**Run Rejection Conditions**
- Repo's default_environment is PROD and `approval_required_for_prod=true` but no approvers are online → BLOCKED
- Resolved Policy requires Human approval but no approval role is assigned → BLOCKED
- No valid Policy can be resolved for the scope → BLOCKED (fallback to System Default)
- Environment is DISABLED → BLOCKED

**Approval Workflow**
- If Policy requires approval, RunPolicy includes `approval_gate=true`.
- Run transitions to "AWAITING_APPROVAL" state (Phase 1 extension).
- Designated approvers (from `approval_roles_required`) receive notification (from `notification_targets`).
- Approver grants or denies via Control Plane endpoint; decision is recorded as HumanOverride (Phase 1.2).
- After approval, run resumes; if denied, run is REJECTED and reason is linked to RunPolicy.

---

## Phase 6.1 Lock

✅ **Phase 6.1 — Control Plane (Governance Layer) is now LOCKED and IMMUTABLE.**

**Immutable Guarantees:**
- All schemas are final.
- All contracts are non-negotiable.
- No retroactive changes to this phase.
- Future extensions must be new phases (6.2, 6.3, etc.) building on this foundation.

**What This Enables:**
- Enterprise organizations to govern AGI Engineer across teams and environments.
- Policy-driven automation without touching the execution engine.
- Full audit trails for compliance, security, and post-incident analysis.
- Deterministic, reproducible governance over autonomous actions.

**Stop here. Do NOT proceed to Phase 6.2.**