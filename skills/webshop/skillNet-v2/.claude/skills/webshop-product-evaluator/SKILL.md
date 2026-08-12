---
name: webshop-product-evaluator
description: >-
  Evaluate visible candidate evidence and recommend one product for detail inspection. Use on a result page after requirements are known and candidates have been extracted. Do not purchase, infer hidden specifications, or choose a candidate with a visible hard failure.
---

# webshop-product-evaluator

## Operating contract

- **Use when:** Use on a result page after requirements are known and candidates have been extracted.
- **Exclude:** Do not purchase, infer hidden specifications, or choose a candidate with a visible hard failure.
- **Input:** Requirement record and candidate evidence from the current page.
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

1. Score hard-constraint evidence before preferences.
2. Treat missing attributes as unknown requiring detail inspection, not as failure or success.
3. Choose the highest-evidence candidate; break ties by fewer unknown hard constraints, then lower price.
4. Return one candidate ID and the constraints to verify on its detail page.

## Verification and completion

The recommendation is valid only when its ID is clickable and the rationale identifies every visible hard pass/fail/unknown.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If all candidates hard-fail, return no recommendation and hand off to pagination or query refinement.

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

Pass the recommendation to `webshop-product-selector`. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Evaluation Logic](references/evaluation_logic.md) only when detailed patterns or examples are needed.
