---
name: webshop-purchase-executor
description: >-
  Execute the single terminal Buy Now action from a valid purchase-ready record. Use only when the purchase gate has passed on the current unchanged detail page and Buy Now is visible. Do not verify products, select options, substitute Add to Cart, or purchase on partial/unknown evidence.
---

# webshop-purchase-executor

## Operating contract

- **Use when:** Use only when the purchase gate has passed on the current unchanged detail page and Buy Now is visible.
- **Exclude:** Do not verify products, select options, substitute Add to Cart, or purchase on partial/unknown evidence.
- **Input:** Current observation and a purchase-ready record tied to that observation.
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

1. Confirm the page and selected variants have not changed since the gate passed.
2. Confirm `Buy Now` exactly matches a current clickable.
3. Emit exactly one `click[Buy Now]` action.
4. Read the next observation and record whether purchase confirmation occurred.

## Verification and completion

Complete only when the environment returns a purchase confirmation or terminal success state.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If purchase confirmation is absent, never repeat Buy Now on unchanged state. Recheck one identifiable missing option; otherwise click Back to Search when visible and abandon the candidate.

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

On terminal success no further action is needed. Otherwise keep the failure internally and let the controller choose one non-repeated recovery action. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Purchase Ui Patterns](references/purchase_ui_patterns.md) only when detailed patterns or examples are needed.
