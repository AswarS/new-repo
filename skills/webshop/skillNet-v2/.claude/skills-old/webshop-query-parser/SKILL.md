---
name: webshop-query-parser
description: Parse a new shopping instruction into normalized fields without deciding how to search. Use when downstream skills require structured fields and no trusted requirement record exists. Do not use after parsing is complete, on page observations alone, or to formulate/execute a search.
---

# webshop-query-parser

## Operating contract

- **Use when:** Use when downstream skills require structured fields and no trusted requirement record exists.
- **Exclude:** Do not use after parsing is complete, on page observations alone, or to formulate/execute a search.
- **Input:** The original instruction text.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Extract product, hard attributes, preferences, quantity, size, brand, and price operators and values.
2. Normalize equivalent units or phrasing without weakening hard constraints.
3. Represent absent fields as unknown rather than guessing defaults.
4. Return the structured fields and a list of unresolved blocking ambiguities.

## Verification and completion

Compare the record against the original instruction and confirm that each number, unit, negation, and strict inequality is preserved.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If parsing is uncertain, preserve the original phrase beside the normalized value; ask only when uncertainty blocks product identity.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass valid fields to a query construction skill; pass blocking ambiguities back for clarification.

## References

- Read [Query Components](references/query_components.md) only when detailed patterns or examples are needed.
