---
name: webshop-option-selector
description: Choose one option from a known option group using explicit requirements and verified consequences. Use when a detail page shows configurable options and the requirement record specifies a value or a legitimate preference rule. Do not default to the first or cheapest option when quantity/size is a hard constraint, and do not buy in the same turn.
---

# webshop-option-selector

## Operating contract

- **Use when:** Use when a detail page shows configurable options and the requirement record specifies a value or a legitimate preference rule.
- **Exclude:** Do not default to the first or cheapest option when quantity/size is a hard constraint, and do not buy in the same turn.
- **Input:** Option group, available values, user constraints, current price, and selected state.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Apply explicit user value first; use cost only as a tie-breaker among equally compliant options.
2. If no value is specified, prefer a standard single unit only when it does not conflict with quantity or value requirements.
3. Emit one exact option click.
4. Re-read the refreshed page and verify price and selection before continuing.

## Verification and completion

Complete when the chosen option is visibly selected and all affected hard constraints remain satisfied.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If option effects or prices are unknown, test at most one plausible option and re-evaluate; if still ambiguous, reject rather than cycling.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Return verified option state to `webshop-product-detail-check`.

## References

- Read [Strategy Docs](references/strategy_docs.md) only when detailed patterns or examples are needed.
