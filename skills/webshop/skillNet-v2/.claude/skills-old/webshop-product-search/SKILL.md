---
name: webshop-product-search
description: Coordinate a bounded product-search stage from validated criteria to a usable result page. Use when the task needs an initial search or a deliberate new search after rejecting prior results. Do not use while a promising product still needs inspection, while variants need selection, or after all hard constraints are verified.
---

# webshop-product-search

## Operating contract

- **Use when:** Use when the task needs an initial search or a deliberate new search after rejecting prior results.
- **Exclude:** Do not use while a promising product still needs inspection, while variants need selection, or after all hard constraints are verified.
- **Input:** Requirement record, current search state, attempted queries, and rejection evidence.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Choose an initial or revised query that preserves product identity and hard attributes.
2. Execute one search and inspect whether the page contains relevant candidates.
3. If no useful candidate exists, revise one query component and try once more.
4. Record both attempts and stop the search stage after two failed distinct queries.

## Verification and completion

A result page is usable only when it contains at least one candidate matching product identity and not visibly violating a hard constraint.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

Never repeat the same query. After two failed queries, return a structured no-result outcome rather than looping.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass usable results to `webshop-result-filter`; pass no-result evidence to the controlling workflow.
