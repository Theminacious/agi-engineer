# Who This System Is For (And Importantly, Who It's Not)

**Audience:** Decision-makers deciding whether AGI Engineer is the right tool for their context

**Goal:** Provide clarity on target vs. non-target use cases. This is a strength, not a limitation.

---

## Built For

### 1. Regulated Teams (Healthcare, Finance, Government)

**Characteristics:**
- HIPAA, SOX, PCI, FedRAMP, CJIS, or similar compliance requirements.
- Audits are regular and external (not internal).
- "Prove what you did" is a legal requirement, not optional.
- Blame and accountability are critical.

**Why AGI Engineer:**
- Immutable ledger is audit-grade evidence.
- Replay proves determinism and reproducibility.
- Human approvals are recorded and undeniable.
- Every decision is queryable and inspectable.
- Compliance artifacts (audit reports, timelines) can be auto-generated from ledger.

**Example:**
- A financial services firm must prove every code change was approved and validated.
- AGI Engineer provides the PLAN_APPROVED event as proof of authorization.
- Replay verifies the change was deterministic.
- Auditors get a JSON report; investigation is complete.

---

### 2. Large, Long-Lived Codebases

**Characteristics:**
- 100K+ lines of code.
- 50+ developers.
- 10+ years of active development.
- High cost of bugs; low tolerance for silent failures.
- Code is reviewed by multiple teams over time.

**Why AGI Engineer:**
- Changes are permanently recorded and queryable.
- A developer in year 10 can ask: "Why was this changed in year 5?"
- Replay verifies the change is still valid under current conditions.
- If a regression is discovered, deterministic rollback is possible.
- Institutional memory is encoded in the ledger, not scattered across chat logs and emails.

**Example:**
- A 20-year-old financial trading system must update an algorithm.
- AGI Engineer records the fix with full context (confidence, risk, policy, approval).
- Five years later, a vulnerability is discovered related to that fix.
- Query the ledger: "Show all runs that modified this file."
- Replay the exact conditions of the original fix.
- Determine if the vulnerability was in the original fix or introduced later.

---

### 3. Environments Where Blame and Accountability Matter

**Characteristics:**
- "Who made this decision?" is not a question for internal discussion; it's a legal inquiry.
- Reversibility is important ("Can we rollback?").
- Hidden failures are unacceptable ("We have to know if something breaks").
- Multi-team environments where decisions must be traceable.

**Why AGI Engineer:**
- Each event records the actor (person or system).
- Human approvals are permanent and undeniable.
- Overrides do not erase history; they create new history.
- Blame is clear: "Who approved this? When? With what information?"
- Rollback is deterministic: reverse decision by emitting an explicit ABORT event.

**Example:**
- A hospital IT team applies a fix to the patient record system.
- The fix causes a data visibility issue, affecting patient care.
- Investigation: "Who approved this fix and why?"
- Ledger: "Dr. Alice Smith approved at 2:30 PM on Jan 12. The approval is in event [5]. Here's the policy she was working under."
- Alice can be asked: "Why did you approve this?" She cannot deny the approval; it's immutable.
- The system can be fixed, and the old run is preserved as evidence.

---

### 4. High-Assurance or Safety-Critical Systems

**Characteristics:**
- Aerospace, medical devices, autonomous vehicles, power grids.
- Certification and safety standards (DO-178C, IEC 62304, ISO 26262).
- Every change must be traceable and justifiable.
- Silent failures are not tolerable; failures must be detectable.

**Why AGI Engineer:**
- Invariants ensure structural integrity of audit trail.
- Deterministic replay satisfies reproducibility requirements.
- Policy binding is recorded; compliance with safety policies is provable.
- Failures are visible (RUN_ABORTED, safety check failures) not silent.
- The ledger is the certification artifact (proof that system was properly governed).

**Example:**
- An aircraft autopilot system is being updated.
- Certification body asks: "Prove this change is safe and has been reviewed."
- AGI Engineer ledger shows: SAFETY_CHECK_PASSED (policy: aerospace-strict), PLAN_APPROVED (by certified engineer), FIX_APPLIED (deterministic).
- Replay verifies the exact changes.
- Certification achieved because the ledger is the proof.

---

## Not Built For

### 1. Hackathon Scripts & Throwaway Code

**Why AGI Engineer is overkill:**
- Setup time (define policy, initialize ledger, get approvals) exceeds utility.
- Ledger overhead is not worth it for code that will be deleted in 2 weeks.
- Approval gates slow down rapid prototyping.

**Better tool:** Copilot, shell scripts, manual fixes.

**Example:**
- "Fix this linting error in this quick script and we're done."
- Using AGI Engineer: Spend 5 minutes setting up policy, 2 minutes creating run, 1 minute approving, 1 minute sealing. Total: 9 minutes.
- Using Copilot: Copilot suggests fix. 30 seconds. Apply it. Done.
- **Wrong tool for the job.**

---

### 2. "Just Fix It Fast" Workflows

**Characteristics:**
- Time-to-fix is the primary metric.
- Auditability is secondary or ignored.
- "Move fast and fix bugs" is the philosophy.
- High tolerance for technical debt and manual cleanup.

**Why AGI Engineer is overkill:**
- Approval gates and governance slow things down.
- Immutable ledger is unnecessary if you're okay with losing history.
- Deterministic replay is unnecessary if you don't care about reproducibility.

**Better tool:** Autonomous bots (Devin, Claude agents), rapid scripting.

**Example:**
- "We have a production bug. Fix it in the next 5 minutes."
- Using AGI Engineer: Define emergency policy, create run, get (emergency) approval, apply fix, seal. Total: 3 minutes (optimized for emergency).
- Using bot: Bot sees bug, fixes it, deploys. Total: 1 minute.
- In an emergency, **speed > audit trail.**

---

### 3. Exploratory or Experimental Code

**Characteristics:**
- "Let's try this idea and see if it works."
- Throwaway prototypes.
- Multiple iterations expected.
- Exploration, not production.

**Why AGI Engineer is overkill:**
- Ledger governance slows down iteration.
- Immutability is antithetical to exploration (can't easily undo).
- Replay is unnecessary if you're just prototyping.

**Better tool:** Interactive IDE, REPL, direct code manipulation.

**Example:**
- "Let me explore how to optimize this algorithm."
- Using AGI Engineer: Initialize run, plan optimization, get approval, execute, inspect, iterate. Repeat 5 times. Total: 20+ minutes of overhead.
- Using IDE: Edit, run, edit, run, edit, run. Total: 3 minutes.
- **Exploration needs agility, not governance.**

---

### 4. Single-Use Automation

**Characteristics:**
- One-time fix across a single repo.
- Never to be repeated.
- No audit trail required.
- Simple, low-stakes change.

**Why AGI Engineer is overkill:**
- Ledger creation and governance is unnecessary for a one-off.
- Replay is unnecessary if it will never happen again.
- Approval processes are ceremony if no one needs to audit it later.

**Better tool:** GitHub Actions, Copilot, manual fix.

**Example:**
- "Format all Python files in this repo to PEP 8 style. Do it once, and we're done."
- Using AGI Engineer: Initialize run, policy setup, approvals, seal. Total: 10+ minutes.
- Using GitHub Action: One-line script, run it, done. Total: 2 minutes.
- **Low-stakes one-offs don't need infrastructure.**

---

## When to Use / When Not to Use

### Use AGI Engineer If:

✅ Code changes must be auditable for compliance.

✅ You need to prove "who decided what, when, and why."

✅ Deterministic replay is valuable (debugging, reproducibility, investigation).

✅ Long-term institutional memory of decisions matters.

✅ Human oversight and approval gates are requirements, not optional.

✅ Silent failures are unacceptable.

✅ Rollback and reverse decisions must be deterministic and recorded.

---

### Don't Use AGI Engineer If:

❌ Speed is the primary metric and audit trail is secondary.

❌ Code is throwaway or experimental.

❌ Approval gates are annoying overhead.

❌ You're okay with losing history after a few weeks.

❌ You want a faster Copilot, not a governance system.

❌ Your environment doesn't require compliance or auditability.

❌ You'd rather have a flexible agent framework than an opinionated ledger.

---

## The Positioning: This Is a Strength

**AGI Engineer is not for everyone. This is intentional.**

Most autonomous coding tools try to be general-purpose:
- "Fast for simple cases, capable for complex cases, flexible for custom workflows."

AGI Engineer is specialized:
- "Purpose-built for regulated, auditable, deterministic code fixing."

**This specialization is a strength because:**

1. **It's honest.** We don't pretend to be everything for everyone.
2. **It's aligned.** If you need what we provide, we provide it well. If you don't, we tell you to use something else.
3. **It's defensible.** We can justify every design decision by reference to governance requirements.
4. **It's trustable.** Skeptics can verify the system works as designed, not guess if it might.

---

## Comparison: Where Each Tool Fits

| Need | Copilot | Bots | Agent Frameworks | **AGI Engineer** |
|------|---------|------|------------------|---|
| **Fast suggestion** | ✅ | - | - | ❌ |
| **Autonomous execution** | - | ✅ | ✅ | ❌ (pre-approval required) |
| **Flexible workflow** | ❌ | ❌ | ✅ | ❌ (opinionated governance) |
| **Auditability** | ❌ | ❌ | ❌ | ✅ |
| **Deterministic replay** | ❌ | ❌ | ❌ | ✅ |
| **Compliance-ready** | ❌ | ❌ | ❌ | ✅ |
| **Immutable ledger** | ❌ | ❌ | ❌ | ✅ |

---

## The Real Questions to Ask

Before choosing AGI Engineer, ask:

1. **Do we need an audit trail?** If no, use Copilot or a bot.
2. **Must we prove compliance?** If yes, AGI Engineer is necessary.
3. **Do we need deterministic replay?** If no, logs are sufficient.
4. **Can we tolerate approval gates?** If no, it's too slow.
5. **How long do we keep code?** If < 1 year, throwaway tools are fine.
6. **Is blame clarity important?** If yes, ledger authority is essential.

---

## Conclusion: Right Tool for the Right Job

AGI Engineer is not a general-purpose autonomous coding tool. It is a specialized governance system for regulated teams, long-lived systems, and environments where proof and accountability matter.

If you need it, there is nothing else like it.

If you don't need it, use something faster and simpler.

Both are correct answers. The question is which one applies to you.
