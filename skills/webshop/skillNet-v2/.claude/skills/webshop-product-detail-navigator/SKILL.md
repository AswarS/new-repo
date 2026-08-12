---
name: webshop-product-detail-navigator
description: >-
  Open one selected product and classify its detail-page controls for downstream inspection. Use when a verified candidate ID is visible on a result page and its detail page is not yet open. Do not rank candidates, select variants, verify hidden attributes, or purchase.
---

# webshop-product-detail-navigator

## Operating contract

- **Use when:** Use when a verified candidate ID is visible on a result page and its detail page is not yet open.
- **Exclude:** Do not rank candidates, select variants, verify hidden attributes, or purchase.
- **Input:** Selected product ID, unresolved-constraint checklist, and current clickables.
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

1. Confirm the ID is the selected candidate and is currently clickable.
2. Emit one `click[product_id]` action.
3. On the returned page identify price, detail tabs, variant groups, Buy Now, and Back to Search controls.

## Verification and completion

Complete only when the returned page corresponds to the selected product and its controls are recorded.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If navigation fails or opens a different product, return to the result page once; do not repeat the same click on unchanged state.

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

Pass page controls and unresolved constraints to `webshop-product-detail-inspector`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Action Protocol](references/action_protocol.md) only when detailed patterns or examples are needed.
