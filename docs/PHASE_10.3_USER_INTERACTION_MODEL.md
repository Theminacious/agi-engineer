# Phase 10.3: User Interaction Model

**Date**: January 13, 2026  
**Status**: Documentation Complete  
**Nature**: No behavior changes, no code modifications, documentation only

## Purpose

This document defines how a user interacts with the AGI Engineer system from initial access through trust verification. This is not a feature specification. It is a description of the interaction model that already exists in the system.

Phase 10.3 introduces no new functionality. It documents the interaction patterns that enable safe, governed, auditable autonomous code fixing.

---

## Section 1: Who The User Is

### Primary User Persona

**Role**: Software engineer, technical lead, or engineering manager with direct repository access.

**Context**:
- Manages codebases with static analysis debt (linting errors, type errors, security warnings)
- Needs to reduce noise in CI/CD pipelines
- Wants to free team time from mechanical fixes
- Requires audit trails for compliance or regulatory reasons
- Skeptical of "AI fixes everything" promises

**Problems They Are Solving**:
1. Hundreds of low-severity linting errors obscuring critical issues
2. Ruff/Pylint/ESLint noise in CI output making real failures hard to spot
3. Junior engineers spending hours on F401 (unused import) fixes
4. Compliance requirements for change traceability
5. Fear that autonomous tools will introduce regressions or security holes

**What They Expect**:
- Transparency: See what will change before it changes
- Control: Approve or reject proposed fixes
- Proof: Verify that the system behaved correctly after the fact
- Safety: No surprises, no silent modifications, no database writes without approval

**What They Do NOT Want**:
- Blind auto-fixing with no review
- Hidden actions that bypass code review
- AI that "learns" from their codebase and does unpredictable things
- Systems that require trusting AI judgment without verification
- Tools that feel like magic instead of infrastructure

---

## Section 2: User Journey (Step-By-Step)

### Step 1: Landing Page (/)

**What The User Does**:
- Visits the AGI Engineer web application
- Reads project description and value proposition
- Understands that this is not Copilot, not Devin, not a chatbot
- Sees "Sign in with GitHub" button

**What The System Does**:
- Displays landing page with clear description of governed autonomous fixing
- Explains: "We find bugs, we propose fixes, you approve, we prove correctness"
- Provides link to authentication

**What Is Visible**:
- Project purpose
- GitHub OAuth integration
- Link to documentation

**What Is Intentionally Hidden**:
- Execution details (user has not authenticated yet)
- Repository access (no repos imported yet)
- Internal agent architecture (not relevant at this stage)

---

### Step 2: Authentication (/auth)

**What The User Does**:
- Clicks "Sign in with GitHub"
- Authorizes AGI Engineer to access repositories (read-only initially)
- Completes OAuth flow

**What The System Does**:
- Redirects to GitHub OAuth
- Requests repository read access (not write access yet)
- Stores JWT token locally in browser
- Creates user session
- Redirects to dashboard

**What Is Visible**:
- GitHub OAuth consent screen
- Repository permissions being requested
- Successful authentication confirmation

**What Is Intentionally Hidden**:
- Token storage mechanism (implementation detail)
- Backend session management
- User database writes

---

### Step 3: Dashboard (/dashboard)

**What The User Does**:
- Arrives at main dashboard
- Sees overview of system status
- Clicks "Import Repository" or similar action
- Selects a repository from GitHub organization

**What The System Does**:
- Fetches user's accessible repositories from GitHub API
- Displays list with metadata (name, language, last commit)
- Waits for user to select repository
- Stores repository metadata (URL, branch, owner)

**What Is Visible**:
- List of accessible repositories
- System status indicators
- Navigation to other sections (Runs, Analytics, AGI Engine, Proof & Governance)

**What Is Intentionally Hidden**:
- Analysis scheduling logic (happens after repository import)
- Agent orchestration details
- Backend execution flow

---

### Step 4: Import Repository

**What The User Does**:
- Selects repository from list
- Confirms branch to analyze (usually main/master)
- Submits import request

**What The System Does**:
- Clones repository to local workspace
- Runs initial scan (Ruff, Pylint, or language-specific linters)
- Detects issues (e.g., 342 linting errors)
- Classifies issues by rule code (F401, W291, E501, etc.)
- Queues analysis run
- Does NOT apply fixes automatically

**What Is Visible**:
- Import confirmation
- Initial issue count
- Run queued indicator
- Link to "View Run"

**What Is Intentionally Hidden**:
- Git clone details
- Linter execution logs
- Rule classifier internal logic
- Safety checker constraints

---

### Step 5: Analysis Execution (Background)

**What The User Does**:
- Waits for analysis to complete
- Can navigate away and return later
- Receives notification when analysis completes (optional)

**What The System Does**:
- Executes multi-agent analysis:
  - Issue detection (linter output)
  - Policy resolution (e.g., RequireApproval)
  - Fix planning (generate proposed changes)
  - Safety checks (no database writes, no API calls, no network access)
  - EDR (Engineering Decision Report) generation
- Writes all events to immutable ledger (append-only)
- Does NOT apply fixes yet
- Does NOT create pull requests yet
- Does NOT commit to repository

**What Is Visible**:
- Run status: "in_progress" → "pending_approval"
- Event count incrementing
- Real-time progress indicators (optional)

**What Is Intentionally Hidden**:
- Internal agent communication
- LLM prompts and responses
- Intermediate state transitions
- Safety checker verdict reasoning

---

### Step 6: Runs List (/runs)

**What The User Does**:
- Navigates to "Runs & Logs"
- Sees list of all runs (past and current)
- Filters by status: pending, in_progress, completed, failed
- Clicks on a specific run to view details

**What The System Does**:
- Fetches all runs from database
- Displays metadata: run_id, repository, branch, status, timestamp
- Shows issue count and fixes count
- Provides links to run detail pages

**What Is Visible**:
- Run history
- Status badges (pending, in_progress, completed, failed)
- Issue and fix counts
- Timestamps

**What Is Intentionally Hidden**:
- Ledger event details (visible in run detail)
- Agent orchestration logs
- Internal execution state

---

### Step 7: Run Detail (/runs/[id])

**What The User Does**:
- Views detailed information about a specific run
- Sees proposed fixes (file, line, rule code, change diff)
- Reviews safety check results
- Decides: Approve or Reject
- Clicks "Approve Plan" button (if confident)

**What The System Does**:
- Displays run metadata (repository, branch, policy, status)
- Shows list of proposed fixes with diffs
- Shows safety check verdict (PASS/FAIL)
- Shows policy enforcement (e.g., RequireApproval means human must approve)
- Records approval event to ledger (actor: user@example.com, role: Human)
- Executes fixes ONLY after approval
- Commits changes to new branch
- Creates pull request (if configured)

**What Is Visible**:
- Proposed fixes with diffs
- Safety check results
- Approval button (if policy requires approval)
- EDR link (Engineering Decision Report)
- Run timeline

**What Is Intentionally Hidden**:
- Agent decision-making process
- LLM temperature settings
- Retry logic
- Internal state machine transitions

**Critical Interaction**:
- User approval is recorded as a ledger event (event_type: PLAN_APPROVED, actor_role: Human)
- Fixes are applied ONLY after this event
- This is not a suggestion—it is a governance requirement

---

### Step 8: Governance & Proof UI (/governance)

**What The User Does**:
- Navigates to "Proof & Governance"
- Sees list of completed runs (frozen snapshots)
- Selects a run to inspect
- Views immutable ledger timeline
- Verifies invariants (sequence contiguous, approval before fix, safety before fix)
- Exports audit log (optional, for compliance)

**What The System Does**:
- Displays read-only view of completed runs
- Shows event timeline in sequence order (0, 1, 2, ..., N)
- Highlights critical events (PLAN_APPROVED, SAFETY_CHECK_PASSED, FIX_APPLIED, RUN_COMPLETED)
- Verifies mathematical invariants:
  1. Sequence contiguous (no gaps)
  2. Terminal event present (RUN_COMPLETED, RUN_ABORTED, or PLAN_REJECTED)
  3. Approval before fix (PLAN_APPROVED precedes all FIX_APPLIED)
  4. Safety before fix (SAFETY_CHECK_PASSED precedes all FIX_APPLIED)
  5. Terminal state match (metadata matches terminal event)
- Shows replay summary (fixes count, duration, violations)

**What Is Visible**:
- Immutable event ledger
- Event sequence numbers, timestamps, actors, roles
- Invariant check results (PASS/FAIL)
- Replay summary (final state, fixes count, violations)
- Audit table (exportable)

**What Is Intentionally Hidden**:
- Execution logic (this is proof, not control)
- Agent internal state
- LLM prompts

**Critical Interaction**:
- User CANNOT trigger execution from this page
- User CANNOT approve plans from this page
- User CANNOT modify ledger data
- This is proof, not control
- Purpose: Verify that the system behaved correctly without trusting AI

---

### Step 9: Trust Verification via Replay & Invariants

**What The User Does**:
- Inspects ledger timeline
- Verifies that human approval (PLAN_APPROVED) occurred before fixes (FIX_APPLIED)
- Verifies that safety checks (SAFETY_CHECK_PASSED) occurred before fixes
- Confirms that no invariants were violated
- Exports audit log for compliance team
- Shows proof to stakeholders (investors, regulators, security auditors)

**What The System Does**:
- Provides cryptographic proof of event ordering
- Demonstrates deterministic replay: same events → same result
- Shows mathematical invariants holding (or failing, if bugs exist)
- Enables verification without trust

**What Is Visible**:
- Complete event history
- Invariant verification results
- Audit export functionality
- Clear "Read-Only" badges

**What Is Intentionally Hidden**:
- Execution triggers (not available in governance UI)
- Approval workflows (not available in governance UI)
- Mutation capabilities (governance is read-only)

**Critical Realization For User**:
"I don't have to trust the AI. I can verify that it followed policy."

---

## Section 3: Execution vs Governance (Critical Distinction)

### What Execution Means

**Definition**: Execution is the process of detecting issues, planning fixes, applying fixes, and committing changes to a repository.

**Where It Happens**:
- Dashboard (/dashboard): Import repository, trigger analysis
- Runs (/runs): Approve plans, execute fixes
- AGI Engine (/v3-analysis): Request intelligent analysis

**Who Controls It**:
- User initiates analysis by importing repository
- Policy determines approval requirements (e.g., RequireApproval)
- User approves or rejects proposed fixes
- System applies fixes ONLY after approval

**What Can Change**:
- Repository state (new commits, branches, PRs)
- Run status (pending → in_progress → completed)
- Ledger (new events appended)

**Permissions Required**:
- GitHub repository write access
- Valid JWT token
- Policy compliance (approval if required)

---

### What Governance Means

**Definition**: Governance is the process of verifying that execution followed policy, without the ability to trigger or modify execution.

**Where It Happens**:
- Proof & Governance (/governance): View frozen run snapshots
- Run detail ledger view: Inspect event timeline

**Who Controls It**:
- No one controls it—it is read-only
- User can view, inspect, verify, export
- User CANNOT approve, execute, or modify

**What Can Change**:
- Nothing—governance views are frozen snapshots

**Permissions Required**:
- Read access to ledger (always granted to authenticated users)

---

### Why Users Cannot Directly Execute Fixes From Governance UI

**Reason 1: Separation of Concerns**
- Execution requires approval workflows, safety checks, policy enforcement
- Governance requires immutability, audit trails, proof generation
- Mixing them would compromise proof integrity

**Reason 2: Temporal Separation**
- Execution happens during the run (events 0 → N)
- Governance happens after the run (frozen snapshot of events 0 → N)
- You cannot approve what has already been executed

**Reason 3: Trust Model**
- Execution requires trusting the system to apply fixes correctly
- Governance removes trust—you verify correctness after the fact
- If governance could execute, it would require trust again

**Reason 4: Compliance Requirements**
- Auditors need read-only access to event logs
- Auditors must not be able to trigger execution
- Governance UI enforces this separation

---

### Why Approvals and Proof Exist

**Approvals Exist Because**:
- Autonomous code changes are high-risk
- Human judgment is required for safety-critical decisions
- Policy enforcement prevents unauthorized modifications
- Compliance may require human-in-the-loop

**Proof Exists Because**:
- Traditional logs are mutable and unverifiable
- Compliance requires audit trails
- Stakeholders need to verify behavior without trusting AI
- Future intelligence upgrades (Phase 11+) require proving that current behavior is safe

**Together They Enable**:
- Safe autonomy (approval ensures human oversight)
- Verifiable autonomy (proof ensures correctness without trust)
- Governed autonomy (policy ensures consistent behavior)

---

### Why This Is NOT Copilot or Devin

#### Not Copilot

**Copilot**:
- Code completion tool
- Suggests code as you type
- No execution, no autonomy, no governance
- Helps write code faster

**AGI Engineer**:
- Code fixing system
- Detects issues, proposes fixes, applies fixes (with approval)
- Full execution, governed autonomy, immutable proof
- Reduces static analysis debt

**Key Difference**: Copilot helps you write code. AGI Engineer fixes existing code autonomously.

---

#### Not Devin

**Devin**:
- Autonomous software engineer
- Takes high-level tasks ("build a login page")
- Self-directed, learning-based
- Opaque decision-making

**AGI Engineer**:
- Autonomous code fixer
- Takes specific repositories and linter outputs
- Rule-based and policy-governed
- Transparent decision-making with audit trails

**Key Difference**: Devin is a teammate. AGI Engineer is infrastructure.

---

#### Not A Chatbot

**Chatbot** (e.g., ChatGPT):
- Conversational interface
- Answers questions, generates text
- No repository access, no code execution
- No governance

**AGI Engineer**:
- Non-conversational system
- Detects issues, proposes fixes, applies fixes
- Direct repository access and execution
- Full governance and proof

**Key Difference**: Chatbots have no agency. AGI Engineer has governed agency.

---

#### Not A Self-Improving AI

**Self-Improving AI**:
- Modifies its own training data or model
- Learns from user behavior
- Unpredictable behavior over time

**AGI Engineer**:
- Fixed agent architecture (no self-modification)
- Does not learn from user feedback
- Deterministic behavior (same input → same output)

**Key Difference**: AGI Engineer does not improve itself. Future phases may improve intelligence, but only with human approval and proof of safety.

---

## Section 4: How This Supports Core AGI Engineer Goal

### Core Goal Restated

The AGI Engineer exists to:
1. Find high-level bugs (unused imports, type errors, security warnings)
2. Fix issues safely (with approval and safety checks)
3. Prevent unsafe autonomy (policy enforcement and proof)
4. Prepare for future intelligence upgrades (Phase 11+)

The user interaction model supports this goal by making intelligence safe to improve.

---

### Finding High-Level Bugs

**User Role**:
- Imports repository with hundreds of linting errors
- System detects all issues automatically
- User does not need to search for bugs manually

**System Role**:
- Runs static analysis (Ruff, Pylint, ESLint)
- Classifies issues by severity and rule code
- Surfaces issues in dashboard

**Interaction Model Contribution**:
- Clear visibility into issue detection
- No hidden analysis—all issues are surfaced
- User understands what the system found

---

### Fixing Issues Safely

**User Role**:
- Reviews proposed fixes
- Approves or rejects plan
- Verifies that fixes are applied only after approval

**System Role**:
- Generates fix plans
- Runs safety checks (no database writes, no API calls, no network)
- Applies fixes ONLY after approval
- Records approval event to ledger

**Interaction Model Contribution**:
- Approval workflow prevents unauthorized changes
- Safety checks prevent dangerous fixes
- User retains control over execution

---

### Preventing Unsafe Autonomy

**User Role**:
- Configures policy (e.g., RequireApproval)
- Verifies that policy was enforced via governance UI
- Inspects ledger to confirm approval occurred before fixes

**System Role**:
- Enforces policy at runtime (no fixes without approval)
- Records all events to immutable ledger
- Verifies invariants (approval before fix, safety before fix)

**Interaction Model Contribution**:
- Policy enforcement is transparent
- Proof is available for verification
- User can verify without trusting AI

---

### Preparing For Future Intelligence Upgrades (Phase 11+)

**Current State (Phase 10.3)**:
- Interaction model is complete
- Governance infrastructure exists
- Proof generation is functional
- Intelligence is FIXED (no self-improvement)

**Future State (Phase 11+)**:
- Intelligence may improve (better fix generation, deeper analysis)
- Interaction model remains unchanged
- Governance ensures that improved intelligence is still safe
- Proof verifies that improved intelligence follows policy

**Interaction Model Contribution**:
"This phase does NOT improve intelligence. It makes intelligence safe to improve."

**Why This Matters**:
- Without governance, improving intelligence is dangerous (unpredictable behavior)
- With governance, improving intelligence is safe (behavior is constrained and verifiable)
- The interaction model ensures that users trust the system even as intelligence improves

---

## Section 5: What This System IS — And IS NOT

### What AGI Engineer IS

#### Governed
- All actions are subject to policy enforcement
- Approvals are required before fixes
- Ledger records all events immutably
- Invariants verify correct behavior

#### Deterministic
- Same input → same output
- Replaying events produces identical state
- No randomness in decision-making (beyond LLM sampling, which is logged)

#### Auditable
- Every action is logged to immutable ledger
- Events include: timestamp, sequence number, actor, role, payload
- Audit logs can be exported for compliance

#### Replayable
- Ledger events can be replayed to reconstruct state
- Replay summary shows final state, fixes count, violations
- Deterministic replay enables verification without trust

---

### What AGI Engineer IS NOT

#### Not A Chatbot
- No conversational interface
- No question-answering functionality
- No text generation for non-code purposes

#### Not A Code Autocomplete Tool
- Does not suggest code as you type
- Does not integrate with IDEs (yet)
- Does not help write new code—only fixes existing code

#### Not A Self-Improving AI
- Does not learn from user feedback
- Does not modify its own training data
- Does not change behavior over time without human intervention

#### Not A Silent Auto-Fixer
- Does not apply fixes without approval (when RequireApproval policy is set)
- Does not hide actions from users
- Does not bypass code review

---

### Critical Distinction: Infrastructure vs Intelligence

**AGI Engineer is infrastructure**:
- Predictable behavior
- Governed by policy
- Auditable and verifiable
- Safe to integrate into CI/CD

**AGI Engineer is not (yet) intelligent**:
- Does not understand semantic bugs (logic errors, off-by-one errors)
- Does not refactor code for readability
- Does not suggest architectural improvements
- Does not "understand" your codebase—it applies rules

**Future Phases May Add Intelligence**:
- Phase 11+ may improve fix generation
- Phase 11+ may add semantic analysis
- Phase 11+ may detect non-linting bugs

**But The Interaction Model Remains**:
- Approval workflows persist
- Governance persists
- Proof generation persists
- Users retain control

---

## Section 6: Phase Lock

### Confirmation: Phase 10.3 Introduces NO Behavior Changes

**No Code Modified**:
- No backend logic changed
- No agent intelligence altered
- No execution flow modified
- No API endpoints added or removed

**No Permissions Altered**:
- User permissions unchanged
- GitHub OAuth scopes unchanged
- Policy enforcement unchanged

**Only Documentation Created**:
- This document (PHASE_10.3_USER_INTERACTION_MODEL.md)
- No behavior changes, no feature additions

---

### Confirmation: All Intelligence Remains Unchanged

**Fix Generation**:
- Still rule-based (Ruff, Pylint, ESLint output)
- No semantic understanding
- No learning from feedback

**Safety Checks**:
- Same constraints (no database writes, no API calls, no network)
- Same verification logic

**Policy Enforcement**:
- Same policies (RequireApproval, NoApproval)
- Same approval workflows

**Ledger Recording**:
- Same event types
- Same immutability guarantees

---

### Confirmation: System Is Now Interaction-Complete

**Phase 10.1 (Complete)**:
- Packaging and architecture documentation
- README rewrite
- ARCHITECTURE.md creation

**Phase 10.2 (Complete)**:
- Read-only Proof & Governance UI
- Ledger visualization
- Invariant verification
- Audit export

**Phase 10.3 (Complete)**:
- User interaction model documentation
- Execution vs governance clarity
- Trust model explanation

**Result**:
- Users understand how to use the system
- Users understand what the system is (and is not)
- Users understand how to verify correctness
- System is ready for intelligence upgrades

---

### Explicit Statement: Phase 11 May Now Safely Improve Intelligence

**Why Phase 11 Is Safe To Begin**:

1. **Governance Infrastructure Exists** (Phase 10.2)
   - Ledger recording is functional
   - Invariant verification is implemented
   - Proof generation is tested

2. **Interaction Model Is Clear** (Phase 10.3)
   - Users know how to approve plans
   - Users know how to verify behavior
   - Users know the system is not a chatbot or auto-fixer

3. **Policy Enforcement Is Active**
   - Approval workflows prevent unauthorized changes
   - Safety checks prevent dangerous fixes
   - Ledger records all actions immutably

4. **Trust Model Is Established**
   - Users do not need to trust AI
   - Users can verify behavior via governance UI
   - Compliance is possible without trust

**What Phase 11 Can Do**:
- Improve fix generation (better patches, fewer false positives)
- Add semantic analysis (detect logic bugs, not just linting errors)
- Improve agent coordination (faster execution, better resource usage)

**What Phase 11 Cannot Break**:
- Approval workflows (still required)
- Safety checks (still enforced)
- Ledger recording (still immutable)
- Governance UI (still read-only)
- Policy enforcement (still mandatory)

**Condition For Phase 11**:
"Intelligence improvements must preserve governance guarantees. If a change would bypass approval, break immutability, or remove proof generation, it is not allowed."

---

## Final Check (Mandatory)

### Verification: No Existing Files Were Modified

✅ Confirmed: Only this documentation file was created.

**Files Created**:
- docs/PHASE_10.3_USER_INTERACTION_MODEL.md

**Files Modified**:
- None

**Files Deleted**:
- None

---

### Verification: No Execution Paths Were Changed

✅ Confirmed: All execution logic remains unchanged.

**Backend Logic**:
- fix_orchestrator.py: Unchanged
- safety_checker.py: Unchanged
- run_ledger.py: Unchanged
- Agent architecture: Unchanged

**Frontend Logic**:
- Dashboard: Unchanged
- Runs UI: Unchanged
- Governance UI: Unchanged (already read-only)

---

### Verification: No Permissions Were Altered

✅ Confirmed: All permissions remain as configured in Phase 10.2 and earlier.

**User Permissions**:
- GitHub OAuth scopes: Unchanged
- JWT token handling: Unchanged

**System Permissions**:
- Repository access: Unchanged
- Approval requirements: Unchanged

---

### Verification: No Intelligence Logic Was Touched

✅ Confirmed: All agent intelligence remains at Phase 10.2 levels.

**Fix Generation**:
- Still rule-based
- No semantic improvements

**Safety Checks**:
- Still constraint-based
- No risk scoring improvements

**Policy Enforcement**:
- Still binary (RequireApproval / NoApproval)
- No adaptive policies

---

## Conclusion

Phase 10.3 defines the user interaction model for AGI Engineer. This model ensures:

1. Users understand what the system is (governed infrastructure, not intelligent assistant)
2. Users know how to use the system (import, approve, verify)
3. Users can verify behavior without trust (governance UI, ledger, invariants)
4. The system is ready for intelligence upgrades (Phase 11+)

**This phase introduces no behavior changes. It documents the interaction patterns that make AGI Engineer safe, auditable, and ready for improvement.**

**Phase 10 is now complete. Phase 11 may proceed.**

---

**Phase 10.3 Complete**: January 13, 2026
