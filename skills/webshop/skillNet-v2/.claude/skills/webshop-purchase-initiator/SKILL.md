---
name: webshop-purchase-initiator
description: >-
  Gate the transition from verified product state to the irreversible purchase action. Use only on a detail page when every hard constraint and required variant has explicit passing evidence. Do not use with unknown constraints, stale price, unselected variants, or absent Buy Now control.
---

# webshop-purchase-initiator

## Operating contract

- **Use when:** Use only on a detail page when every hard constraint and required variant has explicit passing evidence.
- **Exclude:** Do not use with unknown constraints, stale price, unselected variants, or absent Buy Now control.
- **Input:** Final requirement checklist, evidence record, current price, selected variants, and clickables.
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

1. Confirm every hard constraint is pass and none is unknown.
2. Recheck current variant price and required option selections.
3. Confirm exact `Buy Now` text is currently clickable.
4. Produce a purchase-ready record; do not click until these checks pass.

## Verification and completion

Complete when the purchase-ready record lists evidence for identity, attributes, variants, and price.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If a check fails, route to the responsible verifier; if Buy Now is absent, stop rather than substituting another action.

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

Pass only a valid purchase-ready record to `webshop-purchase-executor`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Trajectory Example](references/trajectory_example.md) only when detailed patterns or examples are needed.
