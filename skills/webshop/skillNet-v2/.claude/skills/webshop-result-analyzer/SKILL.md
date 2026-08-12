---
name: webshop-result-analyzer
description: >-
  Extract and compare visible candidates on one WebShop result page. Use when the observation is a result page containing multiple product IDs and visible metadata. Do not use on a detail page, do not claim hidden attributes are satisfied, and do not execute purchase.
---

# webshop-result-analyzer

## Operating contract

- **Use when:** Use when the observation is a result page containing multiple product IDs and visible metadata.
- **Exclude:** Do not use on a detail page, do not claim hidden attributes are satisfied, and do not execute purchase.
- **Input:** Requirement record and the current result-page observation.
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

1. Extract each visible product ID, title, displayed price or range, and rating if relevant.
2. Reject visible hard-constraint violations; mark nonvisible attributes as unknown.
3. Rank remaining candidates by product identity, visible hard-attribute evidence, then preferences.
4. Return the best candidate with passed, failed, and unknown constraints.

## Verification and completion

Complete only when the selected ID is visible and no visible evidence contradicts a hard constraint.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If no candidate survives, return `no_candidate` with reasons; do not invent IDs or repeatedly rescan the same page.

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

Pass a candidate to `webshop-product-selector`; pass `no_candidate` to pagination or search refinement. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Attribute Patterns](references/attribute_patterns.md) only when detailed patterns or examples are needed.
- Read [Execution Example](references/execution_example.md) only when detailed patterns or examples are needed.
