---
name: webshop-product-detail-check
description: >-
  Make the final proceed-or-reject decision from collected product evidence. Use on a detail page after required visible evidence and variant state have been collected. Do not use with unresolved hard constraints, on result pages, or to infer facts absent from evidence.
---

# webshop-product-detail-check

## Operating contract

- **Use when:** Use on a detail page after required visible evidence and variant state have been collected.
- **Exclude:** Do not use with unresolved hard constraints, on result pages, or to infer facts absent from evidence.
- **Input:** Requirement checklist, evidence record, selected variants, current price, and clickables.
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

1. Recheck product identity and current variant-specific price.
2. Require every hard constraint to pass; preferences may rank but cannot override a hard failure.
3. If all hard constraints pass and required options are selected, recommend purchase.
4. Otherwise identify the exact failure or unknown and recommend return to search.

## Verification and completion

A proceed decision requires explicit evidence for every hard constraint and a visible Buy Now control.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

On fail/unknown, emit one `click[Back to Search]` when visible; do not reopen already-checked tabs.

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

Pass a proceed record to `webshop-purchase-initiator`; pass rejection evidence to search control. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Action Guidelines](references/action_guidelines.md) only when detailed patterns or examples are needed.
