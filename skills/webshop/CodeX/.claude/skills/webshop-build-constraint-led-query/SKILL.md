---
name: webshop-build-constraint-led-query
description: Parse a WebShop instruction into product identity, hard attributes, selectable variants, soft preferences, and price limits, then build a compact staged query. Use at the start of a WebShop task or whenever search results are broad, irrelevant, or dominated by one ambiguous term.
---

# Build a Constraint-Led Query

## Condition

Apply before the first `search[...]` and after a search-loop controller requests a materially different query.

## Policy

1. Normalize the instruction into a constraint ledger:
   - `identity`: exact product type; never substitute a related category.
   - `hard`: required brand, compatibility, function, material, dietary property, quantity, dimensions, or pack count.
   - `variant`: color, size, style, scent, flavor, capacity, or other option likely selected on the product page.
   - `soft`: preferences that may be relaxed only after all hard constraints.
   - `price`: strict upper bound; interpret “lower than X” as `< X`.
2. Resolve ambiguous modifiers by attaching them to the most plausible noun. Keep model numbers, unusual colors, measurements, and pack expressions verbatim.
3. Build the first query from `identity + 2–4 highest-information hard constraints`. Include brand/model/compatibility before generic adjectives.
4. Do not put price prose, filler words, or every long-tail preference into the first query. Verify price on results or detail pages.
5. Prepare at most two fallback queries before acting:
   - Query B: preserve identity and rare exact token; replace one synonym.
   - Query C: preserve identity and brand/model/compatibility; remove one low-information descriptor.
6. Pass the ledger unchanged to candidate verification and variant selection. Never silently drop a hard constraint.

Read [references/query-patterns.md](references/query-patterns.md) when the instruction contains dimensions, bundles, compatibility, dietary constraints, or an apparent variant value.

## Termination

Stop when the ledger is complete and Query A plus no more than two materially distinct fallbacks are ready. Hand Query A to the search loop.

## Result

Return or retain:

```text
identity:
hard:
variant:
soft:
price: < amount
queries: [A, B?, C?]
```

The next action is exactly `search[Query A]`.
