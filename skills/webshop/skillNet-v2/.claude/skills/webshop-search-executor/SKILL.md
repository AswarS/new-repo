---
name: webshop-search-executor
description: >-
  Execute one prepared search action and classify the returned page for the next stage. Use when a validated, non-duplicate query is ready and the current page exposes search. Do not formulate requirements, select products, or search again before inspecting the returned observation.
---

# webshop-search-executor

## Operating contract

- **Use when:** Use when a validated, non-duplicate query is ready and the current page exposes search.
- **Exclude:** Do not formulate requirements, select products, or search again before inspecting the returned observation.
- **Input:** One validated query, current observation, and attempted-query history.
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

1. Confirm search is available and the query is not in the attempt history.
2. Emit exactly one `search[keywords]` action.
3. On the next turn classify the outcome as useful results, zero results, irrelevant results, or environment error.

## Verification and completion

Complete when one action was issued and the returned outcome is recorded before any retry.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

For zero/irrelevant results, hand off once to the formulator with evidence; for an environment error retry once, then stop.

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

Send useful results to a result-analysis skill; send failed outcomes to `webshop-search-formulator`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Action Grammar](references/action_grammar.md) only when detailed patterns or examples are needed.
