---
name: webshop-v0-common-control
description: Complete WebShop shopping tasks with a common minimal search, inspection, selection, and purchase workflow. Use as the control condition when testing whether additional constraint, loop, state, or option-gating mechanisms change agent behavior.
---

# WebShop V0 Common Control

## Experimental role

Use this skill as the shared control condition. Follow only the common workflow below. Do not introduce a structured constraint ledger, explicit persistent state record, numerical search-loop limits, or a required-option purchase gate.

## Output contract

- Emit exactly one executable WebShop action per turn.
- The final response must contain only `search[keywords]`, `click[value]`, or `[DONE]`.
- Do not expose analysis, records, checklists, skill names, or multiple actions.
- Use only actions and clickable values supported by the current observation.

## Common workflow

1. Read the original instruction and identify the requested product, important requirements, preferences, and price limit.
2. On the search page, issue one concise query containing the product identity and useful descriptive terms.
3. On a results page, choose a plausible visible product whose title and price do not contradict the instruction.
4. On a product page, inspect visible title, price, options, Description, or Features as needed.
5. Select an option when the instruction clearly requests a visible value.
6. Purchase when the current product appears to satisfy the instruction and `Buy Now` is visible.
7. Emit `[DONE]` after purchase confirmation.

## Common recovery

- When results are poor, revise the query using a reasonable synonym or fewer descriptive terms.
- When a product is unsuitable, return to search and choose another plausible product.
- When a detail tab hides `Buy Now`, return to the product page before purchasing.
- Re-read the observation after every action before deciding the next action.

## Completion

Stop only after the environment confirms the purchase or the environment provides no executable path forward.
