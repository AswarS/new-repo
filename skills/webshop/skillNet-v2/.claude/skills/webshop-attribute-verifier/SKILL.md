---
name: webshop-attribute-verifier
description: >-
  Verify one or more required product attributes against explicit detail-page evidence. Use when a detail-page checklist contains unresolved attribute, price, size, material, or color constraints. Do not use on result pages, treat title absence as proof of failure, or buy within the same turn as option selection.
---

# webshop-attribute-verifier

## Operating contract

- **Use when:** Use when a detail-page checklist contains unresolved attribute, price, size, material, or color constraints.
- **Exclude:** Do not use on result pages, treat title absence as proof of failure, or buy within the same turn as option selection.
- **Input:** Hard-constraint checklist, current page evidence, option state, and clickables.
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

1. Compare the current variant price with the exact user operator and bound.
2. For each attribute record pass, fail, or unknown and cite visible evidence.
3. If a required option is available but unselected, request one exact option click.
4. After the page refresh, reverify price and option state before declaring pass.

## Verification and completion

Complete only when all hard attributes are evidenced and the current selected state is confirmed.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

On hard fail return to search; on unavailable evidence inspect one relevant tab, then reject as unverifiable rather than guessing.

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

Pass verified state to the detail checker or required option to `webshop-attribute-selector`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.
