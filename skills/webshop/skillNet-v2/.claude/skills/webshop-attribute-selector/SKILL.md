---
name: webshop-attribute-selector
description: >-
  Select one explicit required attribute value on a product detail page. Use when a hard requirement maps unambiguously to a currently visible clickable option. Do not use on result pages, choose unspecified defaults, fuzzy-match materially different variants, or purchase.
---

# webshop-attribute-selector

## Operating contract

- **Use when:** Use when a hard requirement maps unambiguously to a currently visible clickable option.
- **Exclude:** Do not use on result pages, choose unspecified defaults, fuzzy-match materially different variants, or purchase.
- **Input:** Required attribute value, current option group, current selected state, and clickables.
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

1. Match the required value to an exact or unambiguously equivalent clickable in the correct option group; never accept a materially different variant.
2. Confirm the option is not already selected.
3. Emit one `click[value]` action.
4. On the refreshed page verify selected state and updated price before selecting another option.

## Verification and completion

Complete when the required value is visibly selected and still satisfies the budget.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If no exact or semantically equivalent option exists, do not click; reject the product. If two options are ambiguous, return the ambiguity.

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

Pass refreshed state to attribute verification; after all options pass, use the purchase gate. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.
