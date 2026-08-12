---
name: webshop-result-filter
description: >-
  Filter visible result-page candidates using hard constraints without treating missing evidence as a pass. Use after result extraction when multiple listings must be reduced to a viable shortlist. Do not use on detail pages, do not select the first item by default, and do not verify hidden features from title absence.
---

# webshop-result-filter

## Operating contract

- **Use when:** Use after result extraction when multiple listings must be reduced to a viable shortlist.
- **Exclude:** Do not use on detail pages, do not select the first item by default, and do not verify hidden features from title absence.
- **Input:** Structured requirements and extracted visible candidate fields.
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

1. Apply product identity and visible hard constraints first.
2. Classify each constraint as pass, fail, or unknown for each candidate.
3. Reject any candidate with a hard fail; retain unknowns for detail inspection.
4. Rank survivors by number and importance of hard passes, then preferences and price.

## Verification and completion

Complete with a shortlist whose entries include evidence and unresolved constraints; an empty shortlist is valid.

Do not treat missing evidence as a pass. After every interface action, re-read the
returned observation before deciding anything else.

## Recovery and stopping

If empty, paginate once when an unseen next page exists; otherwise request one distinct query refinement and stop.

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

Pass the shortlist to `webshop-product-selector` or the empty result to navigation/refinement. A handoff is internal reasoning, not final output; still emit
exactly one legal WebShop action for the current turn.

## References

- Read [Constraint Extraction Guide](references/constraint_extraction_guide.md) only when detailed patterns or examples are needed.
