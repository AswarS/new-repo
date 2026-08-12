---
name: webshop-result-page-navigator
description: Move once between result pages under a bounded pagination policy. Use only after the current result page has been evaluated and has no viable candidate, with an unseen pagination target visible. Do not paginate before evaluating the page, revisit a seen page, or navigate after a viable candidate exists.
---

# webshop-result-page-navigator

## Operating contract

- **Use when:** Use only after the current result page has been evaluated and has no viable candidate, with an unseen pagination target visible.
- **Exclude:** Do not paginate before evaluating the page, revisit a seen page, or navigate after a viable candidate exists.
- **Input:** Current page number, visited-page set, and visible pagination controls.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Prefer an unseen `Next >` page when available.
2. Use `< Prev` only to recover from an accidental navigation, not for exploration.
3. Emit one exact pagination click and add the destination to visited pages.

## Verification and completion

Complete when the page number changes and the destination was not previously evaluated.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If the page does not change, retry once only for an environment error; otherwise stop. After two additional pages, refine the query instead of continuing.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the new page to result analysis or exhausted pagination to search refinement.

## References

- Read [Pagination Controls](references/pagination_controls.md) only when detailed patterns or examples are needed.
