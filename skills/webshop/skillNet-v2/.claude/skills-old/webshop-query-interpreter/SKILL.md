---
name: webshop-query-interpreter
description: Turn a new natural-language shopping request into a structured requirement model and an initial search intent. Use at the start of a new shopping task when the request has not yet been modeled. Do not use on search-result or product-detail observations, and do not execute clicks or purchases.
---

# webshop-query-interpreter

## Operating contract

- **Use when:** Use at the start of a new shopping task when the request has not yet been modeled.
- **Exclude:** Do not use on search-result or product-detail observations, and do not execute clicks or purchases.
- **Input:** The original user instruction.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Extract product type, mandatory attributes, preferred attributes, quantity or pack size, variants, and strict price bound.
2. Separate hard constraints from preferences; preserve comparative words such as `lower than` exactly.
3. Mark missing information only when it blocks a safe search; otherwise retain it as unknown.
4. Produce a compact requirement record and a candidate initial query using product type plus the most discriminative hard attributes.

## Verification and completion

Complete when every explicit user constraint appears once in the structured record and no new constraint has been invented.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If the product type is genuinely ambiguous, request clarification; if only a preference is ambiguous, record it as unknown and continue.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the requirement record to `webshop-search-formulator` or `webshop-product-search`.

## References

- Read [Execution Example](references/execution_example.md) only when detailed patterns or examples are needed.
- Read [Query Patterns](references/query_patterns.md) only when detailed patterns or examples are needed.
