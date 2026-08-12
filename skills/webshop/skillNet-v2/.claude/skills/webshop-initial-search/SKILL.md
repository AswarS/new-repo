---
name: webshop-initial-search
description: >-
  Create and execute the first WebShop search from a validated requirement model. Use only on the initial search page before any query has been attempted for the current task. Do not use to refine a failed query, evaluate results, inspect products, or purchase.
---

# webshop-initial-search

## Operating contract

- **Use when:** Use only on the initial search page before any query has been attempted for the current task.
- **Exclude:** Do not use to refine a failed query, evaluate results, inspect products, or purchase.
- **Input:** A validated requirement record and a visible search action.
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

1. Select product type and two or three discriminative searchable attributes.
2. Keep mandatory identity terms; omit price unless it is part of the product name.
3. Emit one concise `search[keywords]` action.

## Verification and completion

Complete when the query contains the product type, retains critical identity constraints, and contains no unsupported attribute.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If required fields are missing, return to the parser; never submit an empty, duplicate, or price-only query.

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

Pass the returned result page to `webshop-result-analyzer` or `webshop-result-filter`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.
