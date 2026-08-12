---
name: webshop-price-checker
description: Compare one explicit displayed product price with the user's exact budget constraint. Use when both a current price and a numeric budget operator/value are available. Do not use when price is missing, compare a stale pre-variant price, assume currency, or rely on nonexistent scripts.
---

# webshop-price-checker

## Operating contract

- **Use when:** Use when both a current price and a numeric budget operator/value are available.
- **Exclude:** Do not use when price is missing, compare a stale pre-variant price, assume currency, or rely on nonexistent scripts.
- **Input:** Current displayed price, currency, budget operator, and budget value.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Parse the displayed numeric price and preserve its currency.
2. Apply the exact operator: `lower than` is strict `<`; `at most` is `<=`.
3. For a price range, use the price of the selected variant; if unselected, treat compliance as unknown.
4. Return pass, fail, or unknown with the numerical comparison.

## Verification and completion

Complete when the comparison uses the current variant price and exact operator.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If price/currency is missing or malformed, return unknown and prevent purchase; recheck after variant changes.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the verdict to attribute/detail verification.

## References

- Read [Price Patterns](references/price_patterns.md) only when detailed patterns or examples are needed.
