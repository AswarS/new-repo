---
name: webshop-action-executor
description: >-
  Format and emit one already-decided WebShop action using an exact currently available target. Use only after another skill or the current reasoning has selected one exact search term or clickable value. Do not use to choose a product, infer a variant, verify constraints, or plan multiple actions.
---

# webshop-action-executor

## Operating contract

- **Use when:** Use only after another skill or the current reasoning has selected one exact search term or clickable value.
- **Exclude:** Do not use to choose a product, infer a variant, verify constraints, or plan multiple actions.
- **Input:** The current observation and one selected target that is visible or a validated search query.
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

1. Classify the target as a search query or clickable value.
2. Confirm a click target appears exactly in the current observation; preserve its case and spacing.
3. Emit exactly one `search[keywords]` or `click[value]` action.

## Verification and completion

Complete only when the emitted command has balanced brackets and its click value exactly matches a current clickable.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If the target is absent or ambiguous, emit no guessed action and hand back to the selecting skill with the missing target.

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

Return the next observation to the skill responsible for interpreting the resulting page. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.
