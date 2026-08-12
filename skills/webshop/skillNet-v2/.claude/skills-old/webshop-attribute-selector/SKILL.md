---
name: webshop-attribute-selector
description: Select one explicit required attribute value on a product detail page. Use when a hard requirement maps unambiguously to a currently visible clickable option. Do not use on result pages, choose unspecified defaults, fuzzy-match materially different variants, or purchase.
---

# webshop-attribute-selector

## Operating contract

- **Use when:** Use when a hard requirement maps unambiguously to a currently visible clickable option.
- **Exclude:** Do not use on result pages, choose unspecified defaults, fuzzy-match materially different variants, or purchase.
- **Input:** Required attribute value, current option group, current selected state, and clickables.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Match the required value to an exact clickable in the correct option group.
2. Confirm the option is not already selected.
3. Emit one `click[value]` action.
4. On the refreshed page verify selected state and updated price before selecting another option.

## Verification and completion

Complete when the required value is visibly selected and still satisfies the budget.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If no exact or semantically equivalent option exists, do not click; reject the product. If two options are ambiguous, return the ambiguity.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass refreshed state to attribute verification; after all options pass, use the purchase gate.
