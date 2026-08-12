---
name: webshop-v1-constraint-ledger
description: Complete WebShop shopping tasks using the common workflow plus an explicit constraint ledger that preserves product identity, hard requirements, variants, preferences, and price across search and purchase decisions. Use to test the effect of constraint structuring on agent behavior.
---

# WebShop V1 Constraint Ledger

## Experimental role

Use the common workflow with exactly one added mechanism: an explicit constraint ledger. Do not add numerical search-loop limits, a separate persistent execution-state record, or a required-option purchase gate beyond the common workflow.

## Output contract

- Emit exactly one executable WebShop action per turn.
- The final response must contain only `search[keywords]`, `click[value]`, or `[DONE]`.
- Keep the ledger internal. Do not expose analysis, records, checklists, skill names, or multiple actions.
- Use only actions and clickable values supported by the current observation.

## Constraint ledger

Before the first action, internally construct:

```text
identity: exact requested product type
hard: required brand, compatibility, function, material, dietary property, quantity, or dimensions
variant: requested color, size, style, scent, flavor, capacity, or pack value
soft: preferences that may rank otherwise compliant candidates
price: exact operator and amount
```

Apply these rules throughout the task:

- Preserve identity and every hard constraint across all searches and retries.
- Preserve numbers, units, model codes, negations, strict inequalities, and pack expressions exactly.
- Do not silently convert a hard constraint into a preference.
- Treat missing information as unknown rather than guessing a default.
- Reconstruct the same ledger from the original instruction before every candidate or purchase decision.

## Common workflow

1. Build the internal ledger from the original instruction.
2. Search using identity plus the two or three most discriminative hard constraints; omit price prose.
3. On a results page, reject visible contradictions and prefer candidates covering more ledger fields.
4. On a product page, compare visible title, price, options, Description, or Features with the ledger.
5. Select a visible variant value when it exactly matches the ledger.
6. Purchase when the current product appears to satisfy the ledger and `Buy Now` is visible.
7. Emit `[DONE]` after purchase confirmation.

## Common recovery

- When results are poor, change one search term while preserving identity, rare tokens, numbers, and hard constraints.
- When a product is unsuitable, retain the rejection reason and return to search.
- When a detail tab hides `Buy Now`, return to the product page before purchasing.
- Re-read the observation and reconstruct the ledger after every action.

## Completion

Stop only after the environment confirms the purchase or the environment provides no executable path forward.
