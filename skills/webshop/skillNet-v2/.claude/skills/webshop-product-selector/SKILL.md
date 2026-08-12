---
name: webshop-product-selector
description: >-
  Click one already-evaluated candidate to open its detail page. Use when a ranked shortlist exists and the top candidate ID is visible and clickable. Do not use to rank raw results, guess a product ID, or buy directly from the result page.
---

# webshop-product-selector

## Operating contract

- **Use when:** Use when a ranked shortlist exists and the top candidate ID is visible and clickable.
- **Exclude:** Do not use to rank raw results, guess a product ID, or buy directly from the result page.
- **Input:** Top candidate ID, its evidence, unresolved constraints, and current clickables.
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

1. Confirm the candidate has no known hard failure.
2. Confirm the exact product ID appears in current clickables.
3. Record unresolved constraints for detail verification.
4. Emit one `click[product_id]` action.

## Verification and completion

Complete only when the next observation is the selected product detail page.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If the ID is absent or navigation fails, do not repeat blindly; return to result analysis with the changed observation.

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

Pass the detail page and unresolved checklist to `webshop-product-detail-check`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Action Format](references/action_format.md) only when detailed patterns or examples are needed.
