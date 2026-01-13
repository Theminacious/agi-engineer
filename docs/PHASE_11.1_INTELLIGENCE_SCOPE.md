# Phase 11.1: Intelligence Scope & Boundaries Contract

**Date**: January 13, 2026  
**Status**: Documentation Only - No Code Implementation  
**Nature**: Intelligence boundary definition, infrastructure contract

---

## 1. Purpose of Intelligence in AGI Engineer

### Why Intelligence Exists in This System

AGI Engineer currently detects issues using **rule-based analysis**: Ruff, Pylint, ESLint, mypy. These tools identify syntactic and shallow semantic violations (unused imports, type mismatches, naming conventions).

Rule-based analysis cannot detect:
- Architectural violations (layer breaches, circular dependencies)
- Design flaws (god objects, insufficient abstraction)
- Systemic issues (test coverage gaps, configuration drift)
- Semantic bugs (logic errors, concurrency hazards)
- Risk patterns (security misconfigurations, performance anti-patterns)

Intelligence exists to detect these **high-level bugs** while maintaining strict governance guarantees.

### Why Intelligence Is Subordinate, Not Autonomous

Intelligence in AGI Engineer is a **proposal engine**, not an **execution engine**:

- Intelligence **analyzes** and **proposes**
- Humans **approve** and **execute**
- Ledger **records** and **proves**

This subordination is not optional—it is architectural:

1. **Proposal-Only Output**: Intelligence generates analysis reports, not code patches
2. **Human Approval Gate**: Strategies require human approval before execution
3. **Immutable Ledger**: All intelligence outputs are recorded immutably
4. **Deterministic Replay**: Intelligence reasoning is reconstructible and verifiable

Without this subordination, intelligence becomes autonomous and unauditable.

### Why Intelligence ≠ Execution

**Critical Distinction**:

**Intelligence** = Detection + Analysis + Explanation + Proposal  
**Execution** = Approval + Application + Ledger Recording + Verification

Intelligence cannot:
- Approve its own proposals
- Execute fixes without human approval
- Modify code directly
- Trigger workflows
- Commit to repositories
- Create pull requests

These are **exclusively human or policy-enforced actions**.

### Why This Is Infrastructure, Not A Chatbot

This system is not a conversational AI. It has:

- No natural language interface
- No question-answering functionality
- No multi-turn interaction
- No memory between sessions
- No context window management

It is infrastructure:
- Deterministic (same input → same output)
- Stateless (no persistent memory)
- Auditable (every action is logged)
- Governable (policy-enforced boundaries)
- Replayable (all reasoning is reconstructible)

A chatbot would be unpredictable and unauditable. This system is the opposite.

---

## 2. Intelligence Permission Model

### What Intelligence IS Allowed To Do

| Capability | Definition | Example |
|---|---|---|
| **Pattern Detection** | Identify recurring structural patterns across files | "Database access code appears in 47 different files; should be abstracted" |
| **Risk Analysis** | Assess severity, impact, and likelihood of architectural issues | "Circular dependency between module_a and module_b will cause import failures" |
| **Structural Analysis** | Map relationships (dependencies, inheritance, calls) | "ServiceA depends on ServiceB which depends on ServiceA (circular)" |
| **Correlation** | Link issues across multiple files to identify systemic problems | "All 12 database queries lack parameterization; SQL injection risk across application" |
| **Root Cause Hypothesis** | Explain why a problem exists, without proposing fixes | "Missing dependency injection causes tight coupling" |
| **Multi-Strategy Proposal** | Suggest multiple approaches to address a problem | "Option 1: Extract to shared module. Option 2: Use dependency injection. Option 3: Refactor interface." |
| **Impact Estimation** | Estimate scope and magnitude of a problem | "affects 23 files, blocks 8 test suites, increases deployment risk by 15%" |
| **Severity Classification** | Rank issues by priority and urgency | "Critical (blocks deployment), High (architectural debt), Medium (performance), Low (style)" |
| **Uncertainty Acknowledgment** | Explicitly state confidence levels and assumptions | "Confidence 82%, assumes Python 3.10+ syntax" |
| **Prerequisite Identification** | Identify what must happen before a strategy can succeed | "Requires adding test fixtures before refactoring" |

### What Intelligence IS NOT Allowed To Do

| Forbidden Action | Why | Consequence |
|---|---|---|
| **Modify Code** | Intelligence must never write patches directly. All code changes require human approval. | If violated: Intelligence becomes autonomous and unauditable. |
| **Execute Fixes** | Intelligence cannot apply changes or trigger workflows. Execution is exclusively human-approved. | If violated: Governance layer is bypassed. |
| **Approve Strategies** | Intelligence cannot approve its own proposals. Human approval is mandatory. | If violated: No human oversight, system becomes self-directing. |
| **Trigger Workflows** | Intelligence cannot kick off builds, tests, or deployments without explicit human action. | If violated: Uncontrolled execution, violates Phase 10 governance. |
| **Rewrite Large Sections** | Intelligence may not propose replacing >10% of a file or >50 lines of a single function. | If violated: Risk of introducing untestable changes. |
| **Learn Across Runs** | Intelligence must be stateless. Cannot store feedback or adapt behavior across analysis sessions. | If violated: System becomes non-deterministic and non-replayable. |
| **Store Memory** | Intelligence has no persistent context, no session state, no preference learning. | If violated: Violates determinism and auditability requirements. |
| **Self-Trigger Analysis** | Intelligence cannot decide to analyze repositories autonomously. | If violated: Becomes background daemon, loses user control. |
| **Act Without Approval** | All intelligence recommendations require human authorization before execution. | If violated: Loses governance layer, violates policy enforcement. |
| **Access External APIs** | Intelligence cannot make HTTP calls, fetch remote code, or contact external services. | If violated: Security risk, non-determinism, external dependencies. |
| **Modify System Configuration** | Intelligence cannot change policies, ledger settings, or governance rules. | If violated: Circumvents safety gates. |
| **Suppress Warnings** | Intelligence cannot silence its own uncertainty or hide conflicting analyses. | If violated: Hides risks from human approvers. |

---

## 3. High-Level Bug Classes

This section defines the **complete set** of bug categories that AGI Engineer's intelligence is allowed to analyze.

### Category 1: Architectural Violations

**Definition**: Breaches of intended layer boundaries, module contracts, or architectural principles.

**Examples**:
- Presentation layer code directly accessing database
- Business logic scattered across multiple controller files
- Database schema changes not reflected in ORM models
- Bidirectional dependencies between modules (circular dependencies)
- Domain model leaking into API response structures

**Why It Matters**:
- Layer violations cause tight coupling and cascading failures
- Circular dependencies cause import errors and maintenance nightmares
- Architectural decay accelerates exponentially once started

**Why It Is Safe To Detect**:
- Can be analyzed statically via import analysis and dependency graphs
- Root causes are structural, not semantic
- Detection is deterministic and reproducible

**Why Detection ≠ Execution**:
- Detecting "layer boundary breach" is analysis
- Proposing "move code to correct layer" is strategy
- Actually moving the code requires human approval and planning

**Severity Levels**:
- **Critical**: Breaks application startup or core workflows
- **High**: Causes runtime errors under common usage
- **Medium**: Increases maintenance burden or tech debt
- **Low**: Style or organizational issue

---

### Category 2: God Objects / God Services

**Definition**: Classes or modules that handle too many responsibilities, violating single-responsibility principle.

**Examples**:
- 5,000+ line utility class doing validation, parsing, formatting, and caching
- Service class with 40+ public methods serving 8 different business domains
- Database abstraction class that also handles HTTP routing and authentication
- Factory that creates instances, configures them, and manages their lifecycle

**Why It Matters**:
- Massive objects are expensive to test and maintain
- Changes to one concern break unrelated functionality
- High cognitive load for developers
- Increased likelihood of bugs

**Why It Is Safe To Detect**:
- Measurable via lines of code, method count, concern density
- Can identify using cohesion analysis and call graph inspection
- Detection is static and deterministic

**Why Detection ≠ Execution**:
- Detecting "class has 45 methods" is analysis
- Proposing "split into 3 focused classes" is strategy
- Actually refactoring requires design review and testing

**Severity Levels**:
- **Critical**: Single point of failure, all features depend on this class
- **High**: Difficult to test, difficult to extend, causes frequent bugs
- **Medium**: Code smell, maintenance burden, increases onboarding time
- **Low**: Organizational preference, not a technical problem

---

### Category 3: Broken Invariants

**Definition**: Violations of expected system properties or postconditions.

**Examples**:
- Constructor that can raise exceptions (invariant: constructed objects are valid)
- Database getter that sometimes returns None without error handling
- Cache that can become inconsistent with source of truth
- Permission check in controller but not in service layer (invariant: all data access is protected)
- Test file existence without corresponding source file (invariant: all tests have implementation)

**Why It Matters**:
- Broken invariants are subtle bugs that manifests far from the root cause
- Lead to data corruption, security failures, or application crashes
- Difficult to debug once broken

**Why It Is Safe To Detect**:
- Can be identified via control flow analysis, error handling inspection, and contract verification
- Violations are usually local (within a function or module)
- Detection is deterministic

**Why Detection ≠ Execution**:
- Detecting "constructor can fail" is analysis
- Proposing "refactor to factory pattern" is strategy
- Implementing the pattern requires design approval and testing

**Severity Levels**:
- **Critical**: Breaks core assumptions, causes data corruption
- **High**: Can cause runtime errors, security vulnerabilities
- **Medium**: Indicates missing error handling or edge case management
- **Low**: Defensive programming, not currently failing

---

### Category 4: Circular Dependencies

**Definition**: Mutual or cyclical dependencies between modules, preventing reuse and complicating testing.

**Examples**:
- module_a imports from module_b which imports from module_a
- ServiceA depends on ServiceB, ServiceB depends on RepositoryA, RepositoryA depends on ServiceA
- Three-way cycle: pkg_a → pkg_b → pkg_c → pkg_a
- Models import from serializers which import from models

**Why It Matters**:
- Circular imports cause initialization failures
- Cannot isolate modules for testing
- Prevents code reuse in other projects
- Creates unpredictable dependency resolution

**Why It Is Safe To Detect**:
- Mechanical detection via import graph analysis
- Deterministic cycle detection algorithm
- No semantic understanding required

**Why Detection ≠ Execution**:
- Detecting cycles is algorithm-based analysis
- Proposing "invert dependency / extract shared module" is strategy
- Implementing requires architectural review

**Severity Levels**:
- **Critical**: Import fails, application won't start
- **High**: Makes testing impossible, blocks refactoring
- **Medium**: Limits code reuse, increases coupling
- **Low**: Organizational preference, system still works

---

### Category 5: Security Misconfigurations

**Definition**: Security settings or practices that reduce system security without immediate failure.

**Examples**:
- Secret API keys hardcoded in configuration files
- Database credentials in version control
- Authentication disabled in non-production code (often left enabled in production)
- CORS policy allowing all origins
- SQL queries built via string concatenation (SQL injection risk)
- Insufficient input validation on user-facing endpoints
- Password hashing without salt

**Why It Matters**:
- Can lead to data breaches, credential leaks, unauthorized access
- Regulatory and compliance violations (PCI-DSS, HIPAA, GDPR)
- Often silent until exploited

**Why It Is Safe To Detect**:
- Pattern-based detection (regex for API keys, known insecure patterns)
- Control flow analysis to trace untrusted input to dangerous operations
- Configuration inspection for insecure defaults
- No code execution required

**Why Detection ≠ Execution**:
- Detecting "hardcoded password" is pattern analysis
- Proposing "use environment variables" is strategy
- Implementing requires security review and credential rotation

**Severity Levels**:
- **Critical**: Allows immediate unauthorized access or data leak
- **High**: Security vulnerability under realistic attack
- **Medium**: Reduces security posture, increases breach impact
- **Low**: Best practice violation, not currently exploitable

---

### Category 6: Performance Anti-Patterns

**Definition**: Code patterns that cause unnecessary resource consumption or slowness.

**Examples**:
- N+1 queries: loop that executes database query per iteration
- Unbounded memory growth: collection that accumulates items without cleanup
- Regex compiled in hot loop (should be compiled once)
- Unnecessary copying: list/dict copied multiple times in single operation
- Blocking I/O in request handler: synchronous database access in async context
- Missing indexes on frequently-queried columns
- Inefficient algorithm: O(n²) where O(n) is possible

**Why It Matters**:
- Causes application slowness, user dissatisfaction, operational cost
- Can prevent system from scaling
- Consumes unnecessary cloud resources

**Why It Is Safe To Detect**:
- Pattern-based (N+1 query detection, loop analysis)
- Control flow analysis (blocking I/O detection)
- Database schema inspection
- No production profiling required (static analysis)

**Why Detection ≠ Execution**:
- Detecting "loop with query inside" is pattern analysis
- Proposing "batch queries / use join" is strategy
- Implementing requires testing and performance validation

**Severity Levels**:
- **Critical**: Application is unusable, timeouts occur in normal usage
- **High**: Noticeable slowness, impacts user experience
- **Medium**: Scales poorly, will become problem as data grows
- **Low**: Micro-optimization, minimal impact

---

### Category 7: Concurrency Hazards

**Definition**: Unsafe concurrent access patterns that can cause race conditions, deadlocks, or data corruption.

**Examples**:
- Shared mutable state without synchronization (race condition)
- Lock acquired in inconsistent order (deadlock risk)
- Check-then-use pattern: value can change between check and use
- Double-checked locking without volatile keyword (incorrect synchronization)
- Callbacks modifying shared state without locks

**Why It Matters**:
- Race conditions cause intermittent, hard-to-reproduce bugs
- Deadlocks cause application hang
- Data corruption under concurrent access
- Failures may not appear in testing

**Why It Is Safe To Detect**:
- Pattern-based detection (shared state without locks)
- Lock order analysis
- Control flow analysis for check-then-use
- Static analysis, no execution required

**Why Detection ≠ Execution**:
- Detecting "shared mutable state" is static analysis
- Proposing "add locks / use thread-safe collection" is strategy
- Implementing requires concurrency review and testing

**Severity Levels**:
- **Critical**: Deadlock or data corruption under concurrent load
- **High**: Race condition under realistic concurrent usage
- **Medium**: Potential issue, may manifest under high concurrency
- **Low**: Defensive programming, minimal risk

---

### Category 8: Test Coverage Blind Spots

**Definition**: Code that is not exercised by any test, indicating untested functionality.

**Examples**:
- Error handling code paths with no corresponding tests
- Feature flags for disabled features, never tested in enabled state
- Fallback code paths that are never exercised
- Dependencies mocked in all tests, never tested with real implementation
- Branch conditions that only occur under rare circumstances

**Why It Matters**:
- Untested code is likely to contain bugs
- Errors discovered post-deployment
- Cannot confidently refactor untested code
- Maintenance burden increases

**Why It Is Safe To Detect**:
- Mechanical coverage analysis (which lines are covered by tests)
- Deterministic and reproducible
- No behavior change required (only detection)

**Why Detection ≠ Execution**:
- Detecting "exception handler not tested" is coverage analysis
- Proposing "add test cases" is strategy
- Actually writing tests requires developer effort

**Severity Levels**:
- **Critical**: Core functionality not tested, failure would impact all users
- **High**: Important code path untested, failure would impact features
- **Medium**: Edge case handling untested, failures are possible but rare
- **Low**: Defensive code rarely exercised, low risk of failure

---

### Category 9: Configuration Drift

**Definition**: Inconsistency between expected and actual configuration, or between different environments.

**Examples**:
- Environment variable documented but not actually used
- Configuration parameter with default value that differs from documented value
- Test environment and production environment using different settings
- Database migration files present but not applied to schema
- Docker image specifies dependencies not installed
- API version documented as v2 but code uses v1

**Why It Matters**:
- Causes unpredictable behavior across environments
- "Works on my machine" failures
- Deployment issues
- Configuration not trustworthy for decision-making

**Why It Is Safe To Detect**:
- Environment inspection (what is actually configured)
- Documentation and code comparison
- Database schema vs migration file inspection
- Static analysis, deterministic

**Why Detection ≠ Execution**:
- Detecting "environment variable not used" is static analysis
- Proposing "remove unused variable / add missing config" is strategy
- Implementation requires verification and deployment

**Severity Levels**:
- **Critical**: Configuration missing or wrong in production, application fails
- **High**: Configuration inconsistent across environments, unpredictable behavior
- **Medium**: Documentation stale, increases maintenance burden
- **Low**: Minor inconsistencies, no functional impact

---

### Category 10: Dependency Misuse

**Definition**: Incorrect, unsafe, or anti-pattern usage of external dependencies.

**Examples**:
- Using deprecated API without migration plan
- Importing internal implementation (not public API)
- Using optional dependency unconditionally (crashes if not installed)
- Version constraints too loose (semver allows breaking changes)
- Dependency version mismatch between requirements and lock file
- Using entire library for single function
- Dependency with security vulnerabilities (known CVE)

**Why It Matters**:
- Deprecated API will break in future versions
- Internal API changes without warning
- Missing dependencies cause runtime failures
- Loose version constraints cause non-reproducible builds
- Security vulnerabilities allow attacks

**Why It Is Safe To Detect**:
- Static analysis of import statements
- Dependency manifest inspection
- Known vulnerability database lookup
- Deprecation tracking (via version manifests)

**Why Detection ≠ Execution**:
- Detecting "uses deprecated API" is static analysis
- Proposing "upgrade to new API" is strategy
- Implementing requires compatibility review and testing

**Severity Levels**:
- **Critical**: Uses known security vulnerability, application is exploitable
- **High**: Uses deprecated API slated for removal, will break in next major version
- **Medium**: Uses internal API, will break if implementation changes
- **Low**: Sub-optimal usage, not currently broken

---

### Category 11: API Contract Violations

**Definition**: Usage of external APIs that violates documented contracts or assumptions.

**Examples**:
- Calling method with invalid parameter types
- Using endpoint in violation of rate limits
- Assuming response has field that is optional
- Ignoring documented error codes
- Using synchronous blocking call where async is required
- Assuming order of array elements (not guaranteed by API)

**Why It Matters**:
- API changes may break code silently
- Runtime errors when assumptions are violated
- Surprises during integration with real services

**Why It Is Safe To Detect**:
- Static type checking against API definitions
- API documentation inspection
- Control flow analysis of error handling
- Interface contract verification

**Why Detection ≠ Execution**:
- Detecting "method called with wrong type" is type checking
- Proposing "fix argument types / add error handling" is strategy
- Implementing requires code review and testing

**Severity Levels**:
- **Critical**: Violates API contract, guaranteed runtime failure
- **High**: Assumes optional field always present, fails without field
- **Medium**: Ignores possible error, code path untested
- **Low**: Sub-optimal, not currently failing

---

### Category 12: Abstraction Leakage

**Definition**: Implementation details of modules exposed through interfaces or violated layers.

**Examples**:
- Data model returned directly from API (client depends on schema)
- Database table structure visible in application code
- Cache implementation exposed as interface
- Internal exceptions propagated to callers
- Internal helper functions marked public
- Business logic leaking into view layer

**Why It Matters**:
- Cannot change implementation without breaking clients
- Increases coupling
- Makes refactoring difficult
- Violates separation of concerns

**Why It Is Safe To Detect**:
- Interface inspection (what is publicly exposed)
- Dependency analysis (what is imported where)
- Control flow tracking (where internal details are used)
- Static analysis, deterministic

**Why Detection ≠ Execution**:
- Detecting "data model directly exposed" is interface analysis
- Proposing "wrap in data transfer object / abstraction" is strategy
- Implementing requires refactoring and testing

**Severity Levels**:
- **Critical**: Breaking change required for any implementation change
- **High**: Clients depend on implementation details
- **Medium**: Makes refactoring difficult, increases coupling
- **Low**: Style issue, works correctly

---

## 4. Intelligence Output Contract (Structural)

All intelligence analysis outputs must conform to this strict contract. Outputs that violate this contract are rejected and must be reanalyzed.

### Output Schema

Each intelligence result must contain the following fields:

```
{
  "analysis_id": "string (UUID)",
  "timestamp": "ISO 8601 datetime",
  "repository_url": "string",
  "branch": "string",
  "bug_class": "enum (one of the 12 categories above)",
  "problem_statement": "string (plain English, <500 chars)",
  "affected_files": [
    {
      "path": "string (relative path)",
      "line_range": "string (format: 'start-end' or 'start' for single line)",
      "severity": "string (Critical, High, Medium, Low)"
    }
  ],
  "risk_level": "string (Critical, High, Medium, Low)",
  "risk_explanation": "string (plain English, why this is a risk, <1000 chars)",
  "root_cause_hypothesis": "string (why does this problem exist, <500 chars)",
  "impact_radius": {
    "files_affected": "integer",
    "functions_affected": "integer",
    "estimated_users_impacted": "enum (none, some, most, all)",
    "deployment_risk": "enum (none, low, medium, high, critical)"
  },
  "suggested_strategies": [
    {
      "strategy_id": "string (UUID)",
      "strategy_name": "string (<100 chars)",
      "description": "string (plain English, <500 chars)",
      "effort_estimate": "enum (trivial, small, medium, large, very_large)",
      "prerequisite_actions": "array of strings",
      "assumptions": "array of strings",
      "risks": "array of strings"
    }
  ],
  "confidence_level": "integer (0-100, percent)",
  "confidence_explanation": "string (why we are or are not confident, <300 chars)",
  "conflicting_analyses": [
    "array of analysis_ids that contradict this one"
  ],
  "requires_human_decision": "boolean",
  "decision_required_for": "string (if true, explain what decision is needed)",
  "ledger_event_type": "string (ANALYSIS_COMPLETED)",
  "metadata": {
    "analysis_duration_ms": "integer",
    "files_scanned": "integer",
    "lines_analyzed": "integer",
    "patterns_matched": "array of strings"
  }
}
```

### What Outputs CAN Contain

✅ Pattern descriptions ("This class has 47 public methods")  
✅ Risk assessments ("High risk of import failures under circular dependency")  
✅ Root cause hypotheses ("Tight coupling due to lack of dependency injection")  
✅ Multiple strategies ("Option 1: Extract layer. Option 2: Use factory pattern. Option 3: Refactor interface.")  
✅ Severity and confidence levels  
✅ Assumptions and prerequisites ("Assumes Python 3.10+, requires adding test fixtures")  
✅ File paths and line ranges (read-only, no modifications)  
✅ Impact estimations ("affects 23 files, blocks 8 tests")  

### What Outputs CANNOT Contain

❌ Patch diffs or code snippets  
❌ Direct rewrites ("Replace line 47 with X")  
❌ Execution commands ("Run: git commit -m ...")  
❌ Approval declarations ("This fix should definitely be applied")  
❌ Large-scale refactoring instructions  
❌ Recommendations for specific libraries or implementations  
❌ Assumptions hidden in confidence scores  
❌ Suppressed uncertainties ("I'm not sure but proceeding anyway")  

### Output Validation Rules

1. **Every analysis must have ≥2 suggested strategies** (at least present human with choices)
2. **Every strategy must have prerequisites** (intelligence cannot assume clean state)
3. **Confidence < 80% requires explicit explanation** (low confidence must be visible)
4. **File paths are relative to repo root** (no absolute paths, no system-specific paths)
5. **Severity per file is independent** (same problem can have different severity in different files)
6. **Estimates must include uncertainty** ("23 ± 5 files affected" not just "23 files")
7. **Conflicts must be explicit** (if this analysis contradicts prior analysis, state it)
8. **All assumptions must be testable** (should be possible to verify assumption is true)
9. **Strategy prerequisites must be ordered** (Action A before Action B)
10. **All human decisions must be explicit** (what question requires human judgment)

---

## 5. Governance Integration

### How Intelligence Outputs Become Ledger Events

1. **Intelligence Analysis Completes**
   - System generates analysis output conforming to Section 4 schema
   - Analysis is validated against schema (rejects if invalid)

2. **Ledger Event Created**
   - Event type: `INTELLIGENCE_ANALYSIS_COMPLETED`
   - Event timestamp: When analysis finished
   - Event actor: System (role: Analyzer)
   - Event payload: Complete analysis output (immutable copy)

3. **Event Is Appended To Ledger**
   - Appended to immutable ledger (cannot be edited or deleted)
   - Assigned sequence number
   - Cryptographically signed

4. **Analysis Appears in Governance UI**
   - Governance UI reads ledger and reconstructs analysis timeline
   - Each analysis is displayed in read-only format
   - User can view rationale, strategies, and confidence level
   - Cannot modify or approve analysis (governance is read-only)

### Why Outputs Are Immutable

Once an intelligence output is recorded, it **cannot be modified**, because:

1. **Auditability**: Historical record must be preserved for compliance
2. **Determinism**: Changing past analyses breaks replay integrity
3. **Proof**: If analysis can change, proof of correctness is invalidated
4. **Replay**: Replaying run must produce same analysis sequence

If analysis is wrong, the system does not edit the past analysis—it **creates a new, contradicting analysis** (recorded separately).

### How Outputs Appear in Governance UI

The Governance dashboard will display:

- **Intelligence Timeline**: Chronological list of all analyses performed
- **Confidence Level**: Visual indicator (⭐⭐⭐⭐ = 80-100%, ⭐⭐⭐ = 60-80%, etc.)
- **Risk Assessment**: Color-coded severity (Critical = red, High = orange, Medium = yellow, Low = blue)
- **Strategy List**: All proposed strategies with effort estimates
- **Assumptions**: Testable assumptions underlying the analysis
- **Prerequisites**: Actions that must occur before strategies can succeed

Users can:
- View complete analysis rationale
- Compare multiple analyses of same problem
- See which analyses led to approved strategies
- Export analyses for compliance review

Users **cannot**:
- Edit analyses
- Delete analyses
- Approve strategies from governance UI (approval happens in execution UI)
- Suppress analyses

### Why Replay Must Reconstruct Intelligence Reasoning

When a run is replayed (from ledger events), it must reconstruct **all intelligence reasoning** because:

1. **Determinism**: Same events must produce same analysis sequence
2. **Verification**: Auditors must be able to see why fixes were proposed
3. **Traceability**: Regulatory requirements for complete decision audit trails
4. **Debugging**: If something went wrong, replay shows exactly what was analyzed

This means:
- Intelligence must be **deterministic** (same input → same output)
- Intelligence must **log all reasoning** (rationale preserved in ledger)
- Intelligence must **not have side effects** (should be replayable indefinitely)

### Why Humans Approve Strategies, Not AI

Critical distinction in approval workflow:

**Intelligence proposes strategies** (analysis output)  
**Humans approve strategies** (approval event)  
**System executes approved strategy** (execution event)  

Intelligence **cannot**:
- Approve its own strategies
- Declare one strategy better than another
- Force execution of preferred strategy
- Prevent human from choosing different strategy

Humans must decide:
- Which strategy to pursue
- Whether strategies are feasible
- How to sequence prerequisite actions
- Whether to defer decision or abort analysis

This is **human-in-the-loop by design**, not by policy.

---

## 6. Safety & Failure Model

### What Happens If Intelligence Is Uncertain

If confidence level < 60%, the system:

1. **Flags uncertainty explicitly** in output
2. **Surfaced to human reviewer** before any decision is made
3. **Does NOT recommend strategy** (leaves choice to human)
4. **Suggests additional analysis** if available (e.g., "run profiler to confirm", "add instrumentation")
5. **Records uncertainty** in ledger for future reference

Example:
```
Confidence: 47%
Reason: "Cycle detection assumes static imports; 
  dynamic imports may change result. Requires runtime analysis to confirm."
Suggested Action: "Add runtime import tracking, re-analyze with real data."
```

Humans have full visibility and can:
- Decide to proceed anyway ("I understand the risk")
- Request additional analysis before deciding
- Defer the issue and move on
- Escalate to architecture review

### What Happens If Multiple Analyses Conflict

If two intelligence analyses propose contradictory findings:

1. **Both analyses recorded** in ledger (not suppressed)
2. **Conflict flagged explicitly** in each analysis
3. **Presented to human** with both perspectives
4. **Human decides** which analysis to trust or if both are partially correct
5. **Decision and rationale recorded** in ledger

Example:
```
Analysis A: "Circular dependency between module_x and module_y"
Analysis B: "No circular dependency; imports are conditional and order-dependent"

Both recorded. Humans and specialists must investigate.
Possible outcomes:
- Analysis A is correct, refactor required
- Analysis B is correct, Analysis A had false positive
- Both are partially correct, complex refactoring needed
```

This is not a problem—it is **transparency**.

### How Disagreement Is Handled

When intelligence produces conflicting results:

1. **All analyses are presented**
2. **Not averaged or merged** (keeps complete information)
3. **Confidence levels remain independent** (don't modify based on conflict)
4. **Human decides** without system "picking one"
5. **Decision is recorded** (which analysis was accepted and why)

This prevents:
- Silent suppression of dissenting views
- Loss of information through averaging
- System hiding uncertainty
- Biased selection toward "confident" analyses

### Why Aborting Is Safer Than Guessing

If intelligence cannot confidently analyze something, it **aborts and reports uncertainty** rather than proceeding with low confidence.

**Never** do this:
```
(Confidence 40%)
OK let's guess... proceeding with strategy anyway
```

**Always** do this:
```
Confidence: 40%
Reason: [explanation]
Status: REQUIRES_HUMAN_DECISION
Proposed Action: Request additional analysis, architect review, or defer
```

This prevents:
- Silent failures based on bad confidence
- Guessed fixes that backfire
- Wasted effort on low-probability strategies
- Loss of user trust

---

## 7. Explicit Non-Goals

This section lists capabilities that AGI Engineer will **never have**, even in future phases.

### 1. Self-Modifying Intelligence

**Never**: Intelligence that modifies its own parameters, heuristics, or decision logic based on experience.

**Why**: Violates determinism, defeats auditability, prevents replay of past behavior.

---

### 2. End-To-End Autonomy

**Never**: Intelligence that performs all steps (analysis → decision → execution → verification) without human approval.

**Why**: Governance model explicitly requires human approval between strategy proposal and execution.

---

### 3. Self-Healing Code

**Never**: Automatic fixes applied without approval whenever an issue is detected.

**Why**: Violates approval-before-execution principle. All fixes require human authorization.

---

### 4. Autonomous Refactors

**Never**: Large-scale code restructuring (rewriting >10% of file, moving functions across modules) without explicit human-approved strategy and review.

**Why**: Refactoring requires architectural review and testing. Cannot be automated beyond mechanical transforms.

---

### 5. Continuous Background Execution

**Never**: Intelligence that continuously analyzes repositories in background without user triggering.

**Why**: Loses user control, becomes unauditable daemon process, prevents explicit approval.

---

### 6. Silent Fixes

**Never**: Fixes applied without appearing in ledger or being visible to users and auditors.

**Why**: Violates governance principle that all actions are recorded and visible.

---

### 7. Learning From User Feedback

**Never**: Intelligence that adapts behavior based on feedback ("user rejected this fix, so don't suggest similar fixes in future").

**Why**: Makes system non-deterministic, breaks replay, violates statelessness requirement.

---

### 8. Implicit Preferences Or Memory

**Never**: System preferences that carry between runs or sessions ("this user prefers option A over B").

**Why**: Hides decision logic from auditors, makes behavior unpredictable.

---

### 9. Predictive Analysis

**Never**: "Predicting" problems that don't yet exist in code ("this change might cause issues even though it's valid now").

**Why**: Confuses possible futures with current problems, lacks verifiability.

---

### 10. Code Generation Beyond Fixes

**Never**: Creating new code files or implementing features (only fixing broken existing code).

**Why**: Feature development requires design decisions, not automation.

---

## 8. Phase Lock Statement

### Phase 11.1 Is Documentation-Only

This document defines intelligence boundaries. **No code is written in Phase 11.1.**

### No Behavior Changes Introduced

- All existing systems function unchanged
- No execution paths modified
- No new APIs added
- No permissions altered
- No intelligence implementation attempted

### Intelligence Implementation Is Deferred To Phase 11.2

Phase 11.2 will implement intelligence conforming to this contract. Until then:
- All intelligence capabilities described here are **not yet available**
- System functions as in Phase 10.3 (rule-based analysis only)
- Governance and ledger systems are ready to record intelligent analyses (once implemented)

### This Contract Is Immutable Once Approved

Once this document is approved (code review, security review, compliance review):

1. **Cannot be modified without new phase** (creates Phase 11.3 or later)
2. **Implementation must conform** to this contract
3. **Violations are implementation bugs** (not design changes)
4. **All future phases bind to these constraints** (Phase 12+)

---

## Summary Table: What Phase 11 Brings vs What It Doesn't

| Aspect | What Phase 11 Adds | What Remains Unchanged |
|---|---|---|
| **Analysis** | Architectural, design, systemic bug detection | Rule-based linting (Ruff, Pylint) remains |
| **Output Format** | Structured intelligence results (per Section 4) | Ledger event format unchanged |
| **Governance** | Intelligence events recorded in ledger | Approval workflows unchanged |
| **Execution** | Strategies proposed by intelligence | Approval/execution workflow unchanged |
| **Approval** | Human approval of intelligence strategies | Approval remains mandatory |
| **User Control** | More issue categories detected | User retains full control |
| **Auditability** | More detailed ledger of reasoning | All outputs remain immutable |
| **Autonomy** | Intelligence can analyze, NOT execute | No autonomous execution introduced |
| **Trust Model** | Users can verify intelligent analysis | Verification-based trust model unchanged |

---

## Implementation Readiness Statement

This contract is **implementation-ready**. A team can implement Phase 11.2 (intelligence implementation) by:

1. **Accepting this contract** as requirements specification
2. **Implementing each bug class** with appropriate static analysis
3. **Generating output** conforming to Section 4 schema
4. **Integrating with ledger** via Section 5 integration points
5. **Testing** against Phase 11.1 constraints

Phase 11.2 success = Intelligent analysis passes all Section 2-8 constraints.

---

**Phase 11.1 Complete**: January 13, 2026  
**Status**: Documentation approved, awaiting Phase 11.2 implementation
