---
name: webshop-query-parser
description: >-
  Parse a new shopping instruction into normalized fields without deciding how to search. Use when downstream skills require structured fields and no trusted requirement record exists. Do not use after parsing is complete, on page observations alone, or to formulate/execute a search.
---

# webshop-query-parser

## Operating contract

- **Use when:** Use when downstream skills require structured fields and no trusted requirement record exists.
- **Exclude:** Do not use after parsing is complete, on page observations alone, or to formulate/execute a search.
- **Input:** The original instruction text.
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

1. Extract product, hard attributes, preferences, quantity, size, brand, and price operators and values.
2. Normalize equivalent units or phrasing without weakening hard constraints.
3. Represent absent fields as unknown rather than guessing defaults.
4. Return the structured fields and a list of unresolved blocking ambiguities.

## Verification and completion

Compare the record against the original instruction and confirm that each number, unit, negation, and strict inequality is preserved.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If parsing is uncertain, preserve the original phrase beside the normalized value. When product identity remains uncertain, use the literal identity phrase in one conservative search rather than inventing a replacement.

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

Pass valid fields to a query construction skill; pass blocking ambiguities back for clarification. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Query Components](references/query_components.md) only when detailed patterns or examples are needed.
