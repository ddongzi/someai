---
description: Assess the current codebase against the feature's spec, plan
---

You are performing convergence (coverage) assessment for **the current task**.
If the user provides input (e.g., a scope or focus area), treat it as the
anchor for the current task and you **MUST** consider it before proceeding; if the
input is empty, assess the full specified scope.

## Goal

Close the gap between what a feature's specification, plan and what the
codebase currently implements. Read `spec.md`, `plan.md`as the **sole
source of intent** (with the constitution as governing constraints), assess the current
state of the code, determine which requirements, acceptance criteria, and plan decisions are
unmet, incomplete, or only partially satisfied.

## Operating Constraints
**Constitution Authority**: The project constitution is
**non-negotiable**. Code that violates a MUST principle is the highest-severity finding and
produces a corresponding remediation task.

## Execution Steps

### 1. Initialize Convergence Context
Read these files.
- SPEC = SPECIFY_FEATURE_DIRECTORY/spec.md
- PLAN = SPECIFY_FEATURE_DIRECTORY/plan.md
- CONSTITUTION = `specs/constitution.md` (if present)

### 2. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From spec.md:**

- Functional Requirements (FR-###)
- Success Criteria (SC-###) — include only items requiring buildable work; exclude
  post-launch outcome metrics and business KPIs
- User Stories and their Acceptance Scenarios
- Edge Cases (if present)

**From plan.md:**

- Architecture/stack choices and technical decisions
- Data Model references
- Phases and named touch-points (files/components the plan says will be created or edited)
- Technical constraints

**From constitution (if not an unfilled template):**

- Principle names and MUST/SHOULD normative statements

### 3. Build the Intent Inventory

Create an internal model (do not echo raw artifacts):

- **Requirements inventory**: one stable key per FR-### / SC-### / user-story acceptance
  scenario (e.g. `US1/AC2`), plus the plan decisions and constitution principles that
  impose buildable obligations.
- **Code-scope map**: from the file paths named in `plan.md`, plus a keyword
  search for the concepts each requirement describes, derive the set of source files and
  components in scope for assessment. Bound the assessment to these — do **not** infer
  scope beyond what the artifacts define.

### 4. Assess the Codebase and Classify Findings

For each item in the intent inventory, inspect the current code in scope and produce a
`Finding` only where there is a gap. Classify every finding by **gap type**:

- **`missing`**: the required work is absent from the code entirely.
- **`partial`**: the work exists but does not yet fully satisfy the requirement /
  acceptance criterion / plan decision.
- **`contradicts`**: the code does something that conflicts with stated intent or a
  constitution MUST principle.
- **`unrequested`**: the code contains work not called for by the spec or plan
  (surfaced for awareness — converge does **not** delete code, it only appends a task to
  review/justify or remove it).

Each `Finding` records: the `source_ref` it traces to, the `gap_type`, the
`severity`, the `evidence` (the file/area observed), and the `how_to_fix` description.

**Edge cases:**

- **Little or no code yet**: treat the entire specified scope as `missing` remaining work
  rather than failing.
- **Nothing remains**: produce zero findings and follow the converged branch in Step 7.

### 5. Assign Severity

- **CRITICAL**: violates a constitution MUST principle, or a `missing`/`contradicts` gap
  that blocks baseline functionality of a P1 user story.
- **HIGH**: a `missing` or `partial` gap on a core functional requirement or acceptance
  criterion.
- **MEDIUM**: a `partial` gap on a secondary requirement, or an `unrequested` addition with
  unclear justification.
- **LOW**: minor partial gaps, polish, or low-risk `unrequested` additions.

### 6. Present the In-Session Findings Summary

Before appending anything, output a compact, severity-graded summary (no file writes yet):

## Convergence Findings

```json
[
  {
    "gap_type": "missing",
    "evidence": "Example: no append-only guard detected in path/to/module.py",
    "source_ref": "FR-008",
    "how_to_fix": "Add append-only enforcement",
    "severity": "HIGH"
  }
]
```

**Summary metrics:**

- Requirements / acceptance criteria checked
- Plan decisions checked
- Constitution principles checked (or "skipped — template")
- Findings by gap type (missing / partial / contradicts / unrequested)
- Findings by severity
