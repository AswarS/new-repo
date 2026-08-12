---
name: webshop-product-search
description: >-
  Coordinate a bounded product-search stage from validated criteria to a usable result page. Use when the task needs an initial search or a deliberate new search after rejecting prior results. Do not use while a promising product still needs inspection, while variants need selection, or after all hard constraints are verified.
---

# webshop-product-search

## Operating contract

- **Use when:** Use when the task needs an initial search or a deliberate new search after rejecting prior results.
- **Exclude:** Do not use while a promising product still needs inspection, while variants need selection, or after all hard constraints are verified.
- **Input:** Requirement record, current search state, attempted queries, and rejection evidence.
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

1. Choose an initial or revised query that preserves product identity and hard attributes.
2. Execute one search and inspect whether the page contains relevant candidates.
3. If no useful candidate exists, revise one query component and try once more.
4. Record both attempts and stop the search stage after two failed distinct queries.

## Verification and completion

A result page is usable only when it contains at least one candidate matching product identity and not visibly violating a hard constraint.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

Never repeat the same query. After two failed distinct queries, stop reformulating and click the best currently visible candidate without a known hard failure; if none exists, use one final identity-only search rather than a cosmetic rewrite.

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

Pass usable results to `webshop-result-filter`; pass no-result evidence to the controlling workflow. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.
