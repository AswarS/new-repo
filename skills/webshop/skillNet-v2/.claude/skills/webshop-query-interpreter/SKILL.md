---
name: webshop-query-interpreter
description: >-
  Turn a new natural-language shopping request into a structured requirement model and an initial search intent. Use at the start of a new shopping task when the request has not yet been modeled. Do not use on search-result or product-detail observations, and do not execute clicks or purchases.
---

# webshop-query-interpreter

## Operating contract

- **Use when:** Use at the start of a new shopping task when the request has not yet been modeled.
- **Exclude:** Do not use on search-result or product-detail observations, and do not execute clicks or purchases.
- **Input:** The original user instruction.
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

1. Extract product type, mandatory attributes, preferred attributes, quantity or pack size, variants, and strict price bound.
2. Separate hard constraints from preferences; preserve comparative words such as `lower than` exactly.
3. Mark missing information only when it blocks a safe search; otherwise retain it as unknown.
4. Produce a compact requirement record and a candidate initial query using product type plus the most discriminative hard attributes.

## Verification and completion

Complete when every explicit user constraint appears once in the structured record and no new constraint has been invented.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If the product type is ambiguous, preserve its most literal phrase in one conservative search rather than inventing a category; if only a preference is ambiguous, record it internally as unknown and continue.

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

Pass the requirement record to `webshop-search-formulator` or `webshop-product-search`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Execution Example](references/execution_example.md) only when detailed patterns or examples are needed.
- Read [Query Patterns](references/query_patterns.md) only when detailed patterns or examples are needed.
