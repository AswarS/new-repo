---
name: webshop-product-detail-inspector
description: >-
  Collect explicit evidence for unresolved constraints from a product detail page. Use after opening a product when price, attributes, or variant requirements remain unknown. Do not use on result pages, infer missing facts, or purchase before verification is complete.
---

# webshop-product-detail-inspector

## Operating contract

- **Use when:** Use after opening a product when price, attributes, or variant requirements remain unknown.
- **Exclude:** Do not use on result pages, infer missing facts, or purchase before verification is complete.
- **Input:** Requirement checklist, current detail observation, and visited detail tabs.
- **Output:** Use records, rankings, and handoff data only as internal reasoning. The final response must contain exactly one executable `search[query]` or `click[element]` action and no explanation, record, skill name, or second action.

## Global runtime contract

Classify the current stage before acting:
`START -> SEARCH -> RESULTS -> PRODUCT_DETAIL -> OPTION_SELECTION -> PRE_PURCHASE_VERIFY -> BUY -> DONE`.

Allowed recovery transitions are `RESULTS -> SEARCH`, `PRODUCT_DETAIL -> RESULTS`,
`OPTION_SELECTION -> RESULTS`, and `PRE_PURCHASE_VERIFY -> RESULTS`. Do not jump
straight from unverified results or an unresolved detail page to `BUY`.

Treat the original instruction plus the visible action/observation history as the
cross-skill state. Reconstruct all hard constraints on every turn; do not rely on
an earlier skill's private record being available.

Any workflow instruction to produce, return, pass, or record structured data means
to maintain it as internal reasoning for selecting the next action. It never
authorizes structured data as the final response. A local skill that primarily
analyzes evidence must still select the single next action appropriate to the
current state.

## Workflow

1. Check visible title, price, options, and specification text against every hard constraint.
2. Open at most one unvisited Description or Features tab when required evidence is missing.
3. Classify each hard constraint as pass, fail, or unknown with page evidence.
4. Return a verification record and any required variant selections.

## Verification and completion

Complete when every hard constraint is pass/fail/unknown and no visible contradiction is ignored.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

Reject on any hard fail. If evidence remains unavailable after one relevant detail tab, reject or mark unverifiable; never loop across tabs.

Apply these deterministic controls before emitting the action:

- If the same action already occurred on an equivalent observation, forbid it.
  Treat it as ineffective or already applied and choose a different bounded action.
- Never immediately reverse `click[Next >]` with `click[< Prev]`, or vice versa,
  unless returning to one specifically identified unvisited product.
- Permit at most two materially distinct query reformulations for the same hard
  constraints. Cosmetic rewording does not count as a distinct query.
- Evaluate at most two result pages per query and do not revisit an evaluated page.
- After `click[Buy Now]`, stop on confirmation. If the observation is unchanged,
  never click `Buy Now` again; recheck options once, then abandon the candidate.
- Estimate remaining budget from the action history. With fewer than six actions
  remaining, stop broad exploration, pagination, and cosmetic query changes.
  Use the best already-seen fully verifiable candidate or make one final targeted
  search when no such candidate exists.

Preserve hard constraints during every retry or handoff.

## Handoff

Pass selectable requirements to an option skill, or the completed record to `webshop-product-detail-check`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Action Guidelines](references/action_guidelines.md) only when detailed patterns or examples are needed.
- Read [Trajectory Example](references/trajectory_example.md) only when detailed patterns or examples are needed.
