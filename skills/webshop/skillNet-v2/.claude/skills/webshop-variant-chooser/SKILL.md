---
name: webshop-variant-chooser
description: >-
  Choose a size, quantity, color, or pack variant that satisfies the requirement record. Use when a product detail page exposes multiple variants and at least one variant decision remains. Do not use when no variant is required, on result pages, or to apply an arbitrary default that changes a hard quantity/size constraint.
---

# webshop-variant-chooser

## Operating contract

- **Use when:** Use when a product detail page exposes multiple variants and at least one variant decision remains.
- **Exclude:** Do not use when no variant is required, on result pages, or to apply an arbitrary default that changes a hard quantity/size constraint.
- **Input:** Variant group, clickable values, explicit requirements, current selection, and price.
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

1. Map explicit size/quantity/color requirements to an exact available value.
2. When unspecified, choose a standard single-unit option only if it preserves all hard constraints.
3. Emit one click and re-read the updated page.
4. Verify selection and new price before another variant or purchase action.

## Verification and completion

Complete when every required variant is visibly selected and current price passes.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If no compliant variant exists, reject the product. If the selected state does not change, do not repeat the click.

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

Pass verified variants to the detail checker. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Trajectory](references/trajectory.md) only when detailed patterns or examples are needed.
