---
name: webshop-product-detail-check
description: Make the final proceed-or-reject decision from collected product evidence. Use on a detail page after required visible evidence and variant state have been collected. Do not use with unresolved hard constraints, on result pages, or to infer facts absent from evidence.
---

# webshop-product-detail-check

## Operating contract

- **Use when:** Use on a detail page after required visible evidence and variant state have been collected.
- **Exclude:** Do not use with unresolved hard constraints, on result pages, or to infer facts absent from evidence.
- **Input:** Requirement checklist, evidence record, selected variants, current price, and clickables.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Recheck product identity and current variant-specific price.
2. Require every hard constraint to pass; preferences may rank but cannot override a hard failure.
3. If all hard constraints pass and required options are selected, recommend purchase.
4. Otherwise identify the exact failure or unknown and recommend return to search.

## Verification and completion

A proceed decision requires explicit evidence for every hard constraint and a visible Buy Now control.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

On fail/unknown, emit one `click[Back to Search]` when visible; do not reopen already-checked tabs.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass a proceed record to `webshop-purchase-initiator`; pass rejection evidence to search control.

## References

- Read [Action Guidelines](references/action_guidelines.md) only when detailed patterns or examples are needed.
