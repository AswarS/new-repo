---
name: webshop-episode-controller
description: >-
  Control every WebShop decision turn with a bounded state machine, loop detection, and one-action output. Use on every active WebShop task before choosing the next interface action, regardless of the current page stage. Do not use after terminal purchase confirmation, outside WebShop, or to emit explanations and intermediate records instead of an action.
---

# webshop-episode-controller

## Operating contract

- **Use when:** Use on every active WebShop task before choosing the next interface action, regardless of the current page stage.
- **Exclude:** Do not use after terminal purchase confirmation, outside WebShop, or to emit explanations and intermediate records instead of an action.
- **Input:** The original instruction, complete visible action/observation history, current observation, and maximum step budget.
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

1. Reconstruct the hard constraints from the original instruction and classify the current stage as START, SEARCH, RESULTS, PRODUCT_DETAIL, OPTION_SELECTION, PRE_PURCHASE_VERIFY, BUY, or DONE.
2. Count prior actions, detect unchanged-observation repeats, repeated queries, revisited pages, Next/Prev oscillation, and repeated Buy Now attempts.
3. Choose the responsible local policy for the current stage while preserving all hard constraints and the bounded transition rules.
4. Apply the remaining-budget policy and emit exactly one legal action that advances the task without repeating a known ineffective action.

## Verification and completion

The chosen action must be legal on the current observation, appropriate for the classified stage, non-repeated on unchanged state, and consistent with every hard constraint.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

On a detected loop, forbid the repeated transition and choose one bounded alternative: inspect one unseen evidence source, try one unseen candidate, make one materially different query, or return once to results. With fewer than six actions remaining, stop broad exploration and use only the best already-seen verifiable path.

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

Use the relevant local skill as decision support, but keep this controller's state, loop, budget, and single-action rules in force. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.
