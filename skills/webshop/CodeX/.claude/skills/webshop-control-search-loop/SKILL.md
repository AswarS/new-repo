---
name: webshop-control-search-loop
description: Control WebShop search, pagination, and backtracking with explicit budgets, state memory, and no-repeat rules. Use after submitting a query, when results are irrelevant, when considering Next or Back, or whenever an action or page may be revisited.
---

# Control the Search Loop

## Condition

Apply on every results page and before any repeated search, pagination, `< Prev`, or `Back to Search` action.

## Policy

1. Track `query`, `page`, visited ASINs, rejected ASIN reasons, and the last two observation signatures.
2. Scan the current result page once. Rank visible candidates by:
   `identity/category > brand/model/compatibility > rare hard attributes > price > soft attributes`.
3. Open the best unseen plausible candidate. Do not open a product whose title contradicts identity or compatibility.
4. Paginate only when the page contains plausible same-category results but no good candidate. Allow at most two consecutive `Next >` actions per query.
5. Refine rather than paginate when results are mostly unrelated. Each refinement must change exactly one retrieval decision and must preserve identity plus rare hard tokens.
6. Use at most three distinct queries and inspect at most two candidates per query.
7. Never repeat an identical action from the same observation. Never revisit a rejected ASIN unless a newly selected variant could change the rejection reason.
8. Treat `< Prev` as returning from a candidate and `Back to Search` as resetting to the search form; do not use both to reach the same state.
9. If two consecutive actions yield the same observation signature, declare the action ineffective and choose a different action class.

Read [references/loop-state.md](references/loop-state.md) for the compact state format and refinement rules.

## Termination

Stop searching when any of these holds:

- a candidate passes the evidence gate;
- three materially distinct queries are exhausted;
- six unique candidates are rejected;
- two consecutive state repeats occur;
- the remaining step budget is four or fewer.

On exhaustion, do not buy an arbitrary mismatch. End with `[DONE]` if supported by the environment, or report that no verified match was found.

## Result

Produce one of:

- `OPEN <ASIN>` with the title evidence that made it the best candidate;
- `REFINE <new query>` with the single changed retrieval decision;
- `SEARCH_EXHAUSTED` with rejected candidates and unmet hard constraints.

This policy targets the baseline failure mode in which zero-reward tasks repeatedly reached 29 steps through repeated searches, pagination, and backtracking.
