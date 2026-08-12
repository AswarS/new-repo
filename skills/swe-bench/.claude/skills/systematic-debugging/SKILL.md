---
name: systematic-debugging-optimized
description: Diagnose and fix reproducible repository bugs, test failures, regressions, incorrect output, and unexpected code behavior using evidence-driven root-cause tracing, bounded exploration, regression testing, and clean-diff verification. Use when modifying an existing codebase to correct faulty behavior. Do not use for feature implementation, broad refactoring, formatting-only changes, or tasks without a reported defect.
---

# Systematic Debugging

## Objective

Produce the smallest verified fix for the root cause, with a regression test
and a task-only diff.

Do not equate more searching with better debugging. Each investigation action
must answer a specific unresolved question.

## Required Workflow

Complete these five phases in order:

1. Reproduce
2. Trace
3. Hypothesize
4. Fix
5. Verify

Do not edit production code before completing the implementation gate in
Phase 3.

## Phase 1: Reproduce

Establish a deterministic representation of the bug.

Prefer, in order:

1. An existing failing repository test
2. A new minimal regression test
3. A small executable reproduction
4. An exact expected-output assertion when execution is environment-blocked

Record this artifact:

```text
REPRODUCTION
Command or test:
Actual result:
Expected result:
Failure type: code | environment
```

### Budget

Use at most 3 investigation calls after locating the repository.

If the test does not start because of a missing package, interpreter, path, or
tool, classify it as an environment failure. Do not treat it as evidence about
the code.

## Phase 2: Trace One Broken Value

Trace one incorrect value or behavior backward:

```text
incorrect output
    <- consumer
    <- input representation
    <- producer
```

Find one nearby working comparison case and identify the smallest meaningful
difference.

Record this artifact:

```text
ROOT-CAUSE EVIDENCE
Broken value or behavior:
Consumer:
Representation received by consumer:
Producer:
Representation produced:
Working comparison:
Relevant difference:
```

### Search Order

Use this order:

1. Read the failing test or user-provided reproducer.
2. Search exact identifiers from the failure.
3. Find where the incorrect output or state is constructed.
4. Trace one value backward to its producer.
5. Find one similar working case.
6. Search every direct reader and writer of the representation that may change.

Stop broad exploration once the producer-consumer mismatch is known.

### Budget

Use at most 8 Read, Grep, Glob, or search calls.

If the budget is exceeded, stop and write:

```text
INVESTIGATION CHECKPOINT
Evidence collected:
Exact unanswered question:
Single next action most likely to answer it:
```

Perform only that action before reassessing.

## Phase 3: Form One Hypothesis

State one falsifiable hypothesis:

```text
HYPOTHESIS
I think:
Because:
Minimal experiment:
Expected result if correct:
```

### Implementation Gate

Do not modify production code until all items are satisfied:

- [ ] A failing test, executable reproduction, or exact regression assertion exists.
- [ ] Actual and expected behavior are explicit.
- [ ] The incorrect behavior is traced to a concrete producer-consumer boundary.
- [ ] A working comparison case is identified.
- [ ] One hypothesis explains both the broken and working cases.
- [ ] Direct readers and writers of the representation to be changed were searched.

If any item is missing, perform only the investigation needed to satisfy it.

## Phase 4: Test and Fix

Before editing production code, add or identify the narrowest regression test
that demonstrates the bug.

Then:

1. Make one logical production-code change.
2. Address the identified mismatch at the narrowest safe boundary.
3. Avoid unrelated cleanup, renaming, formatting, and refactoring.
4. Run the narrowest relevant test immediately.

### Choosing the Fix Boundary

Before changing a producer's canonical representation:

1. Search all consumers of that representation.
2. Determine whether consumers expect the current form.
3. Prefer a local matching or conversion boundary when global representation
   changes could affect unrelated consumers.
4. Check parallel code paths that perform the same operation.

For example, if two functions merge the same metadata into different output
forms, inspect both before changing only one.

### Edit Discipline

Each additional edit round requires new evidence:

```text
EDIT REVISION
Previous result:
New evidence:
Revised hypothesis:
Why another edit is necessary:
```

Limits:

- First edit: implement the confirmed hypothesis.
- Second edit: allowed only in response to test or inspection evidence.
- Third edit: return to Phase 2 and reassess the root cause.
- Do not make a fourth edit without identifying a broader design issue.

Do not stack speculative fixes.

## Phase 5: Verify

Verify in this order:

1. Exact regression test
2. Nearby tests for the modified component
3. A relevant alternate configuration or integration path
4. Static checks required by the repository
5. Final diff inspection

Record:

```text
VERIFICATION
Regression:
Nearby tests:
Alternate path:
Static checks:
Limitations:
```

Do not claim the fix is verified if the regression test did not run.

Use precise completion language:

- `Implemented and verified` only when the regression passes.
- `Implemented; integration verification blocked` when the test environment
  prevents execution.
- `Root cause identified; fix not completed` when implementation remains
  uncertain.

## Environment Failure Branch

Use this branch only when a test cannot start.

1. Record the exact interpreter and command.
2. Check whether the missing dependency exists in that interpreter.
3. Look for the repository's configured environment, lockfile, or test command.
4. Use an existing compatible environment when available.
5. Install dependencies only when permitted and within task scope.
6. Attempt at most 3 meaningfully different recovery actions.

Meaningfully different actions include:

- selecting the intended environment;
- installing a confirmed missing dependency;
- using the repository's documented test runner.

The following are not different recovery actions:

- repeating the same command with reordered arguments;
- alternating `pytest` and `python -m pytest` without changing environments;
- rerunning after the same unchanged import error.

After 3 unsuccessful recovery actions:

1. Stop environment exploration.
2. Run a minimal independent or static verification if possible.
3. Mark integration verification as blocked.
4. Preserve the exact blocker in the final report.

## Efficiency Rules

- Do not re-read an unchanged file unless a specific omitted section is needed.
- Do not repeat equivalent commands after the same error.
- Do not search the entire filesystem after locating the repository.
- Do not continue broad search after the data-flow mismatch is identified.
- Do not inspect unrelated subsystems without a concrete dependency path.
- Do not use Todo updates to narrate individual tool calls.
- Create at most five phase-level todos.
- Update todos only when moving between phases.
- Todo completion is not evidence of debugging progress.

## Completion Gate

Before declaring completion, confirm:

- [ ] The regression test exists.
- [ ] The root cause is stated as a producer-consumer or state-transition mismatch.
- [ ] The production change addresses that root cause.
- [ ] Parallel consumers or alternate paths were inspected.
- [ ] The regression passes, or the verification blocker is explicit.
- [ ] The final diff contains only task-related changes.
- [ ] No local settings, generated output, debug code, runner files, or unrelated
      `.gitignore` changes are included.
- [ ] The final claim accurately reflects verification status.

Inspect both repository status and diff before exporting the patch.

## Final Response

Report only:

```text
Root cause:
Fix:
Regression test:
Verification:
Unverified limitations:
Changed files:
```

Keep the report evidence-based. Do not summarize every investigation action.

## Required Adherence Record

At completion, internally evaluate:

```text
ADHERENCE
Reproduction before production edit: yes | no
Explicit producer-consumer trace: yes | no
Single falsifiable hypothesis: yes | no
Direct consumers searched: yes | no
Regression test added or identified: yes | no
Relevant tests passed: yes | no | blocked
Final diff audited: yes | no
Investigation budget exceeded: yes | no
If exceeded, checkpoint recorded: yes | no | not applicable
```

A Skill invocation alone does not count as adherence. The required artifacts and
gates determine whether the workflow was followed.
