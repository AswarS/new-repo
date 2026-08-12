---
name: webshop-option-selector
description: >-
  Choose one option from a known option group using explicit requirements and verified consequences. Use when a detail page shows configurable options and the requirement record specifies a value or a legitimate preference rule. Do not default to the first or cheapest option when quantity/size is a hard constraint, and do not buy in the same turn.
---

# webshop-option-selector

## Operating contract

- **Use when:** Use when a detail page shows configurable options and the requirement record specifies a value or a legitimate preference rule.
- **Exclude:** Do not default to the first or cheapest option when quantity/size is a hard constraint, and do not buy in the same turn.
- **Input:** Option group, available values, user constraints, current price, and selected state.
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

1. Apply explicit user value first; use cost only as a tie-breaker among equally compliant options.
2. If no value is specified, prefer a standard single unit only when it does not conflict with quantity or value requirements.
3. Emit one exact option click.
4. Re-read the refreshed page and verify price and selection before continuing.

## Verification and completion

Complete when the chosen option is visibly selected and all affected hard constraints remain satisfied.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If option effects or prices are unknown, test at most one plausible option and re-evaluate; if still ambiguous, reject rather than cycling.

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

Return verified option state to `webshop-product-detail-check`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Strategy Docs](references/strategy_docs.md) only when detailed patterns or examples are needed.
