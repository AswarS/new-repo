---
name: webshop-search-constructor
description: Construct a syntactically valid WebShop search action from an already-ranked keyword list. Use when product identity and keyword priority are settled but the final action has not been formatted. Do not parse raw requests, rank products, include guessed fields, or rely on nonexistent helper scripts.
---

# webshop-search-constructor

## Operating contract

- **Use when:** Use when product identity and keyword priority are settled but the final action has not been formatted.
- **Exclude:** Do not parse raw requests, rank products, include guessed fields, or rely on nonexistent helper scripts.
- **Input:** Product identity, ordered search terms, and prior queries.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Remove duplicate and empty terms while preserving required identity terms.
2. Join the remaining terms with single spaces and no comparison operators.
3. Confirm the query differs from prior attempts.
4. Emit exactly one `search[keywords]` action.

## Verification and completion

Complete only when brackets are balanced, keywords are nonempty, and all terms come from validated criteria.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If the terms are incomplete or duplicate a prior query, return them to the formulator instead of guessing.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the formatted action to the WebShop environment.

## References

- Read [Query Optimization Guide](references/query_optimization_guide.md) only when detailed patterns or examples are needed.
