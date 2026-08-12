---
name: webshop-search-formulator
description: >-
  Formulate one concise search query from parsed criteria while balancing precision and recall. Use after parsing when a query is needed, or when a failed query has an explicit refinement plan. Do not inspect result pages, choose products, or repeat an unchanged query.
---

# webshop-search-formulator

## Operating contract

- **Use when:** Use after parsing when a query is needed, or when a failed query has an explicit refinement plan.
- **Exclude:** Do not inspect result pages, choose products, or repeat an unchanged query.
- **Input:** Structured product type, hard attributes, preferences, and prior attempted queries if any.
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

1. Require product identity in the query and prioritize discriminative hard attributes; order terms naturally rather than enforcing a fixed first token.
2. Exclude non-searchable price syntax and verbose filler.
3. For refinement, change exactly one aspect: remove the least discriminative preference or add a missing identity synonym.
4. Return one lowercase space-separated `search[keywords]` action.

## Verification and completion

Reject an empty query, a query missing product identity, or any query already present in the attempt history.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

After two unsuccessful reformulations, stop reformulating and hand off with the attempted queries and observed failure.

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

Send the action to `webshop-search-executor`; send exhausted attempts to the controlling workflow. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Search Strategy Guide](references/search_strategy_guide.md) only when detailed patterns or examples are needed.
