---
name: webshop-initial-search
description: Create and execute the first WebShop search from a validated requirement model. Use only on the initial search page before any query has been attempted for the current task. Do not use to refine a failed query, evaluate results, inspect products, or purchase.
---

# webshop-initial-search

## Operating contract

- **Use when:** Use only on the initial search page before any query has been attempted for the current task.
- **Exclude:** Do not use to refine a failed query, evaluate results, inspect products, or purchase.
- **Input:** A validated requirement record and a visible search action.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Select product type and two or three discriminative searchable attributes.
2. Keep mandatory identity terms; omit price unless it is part of the product name.
3. Emit one concise `search[keywords]` action.

## Verification and completion

Complete when the query contains the product type, retains critical identity constraints, and contains no unsupported attribute.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If required fields are missing, return to the parser; never submit an empty, duplicate, or price-only query.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the returned result page to `webshop-result-analyzer` or `webshop-result-filter`.
