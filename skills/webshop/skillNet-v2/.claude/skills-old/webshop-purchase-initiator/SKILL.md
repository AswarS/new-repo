---
name: webshop-purchase-initiator
description: Gate the transition from verified product state to the irreversible purchase action. Use only on a detail page when every hard constraint and required variant has explicit passing evidence. Do not use with unknown constraints, stale price, unselected variants, or absent Buy Now control.
---

# webshop-purchase-initiator

## Operating contract

- **Use when:** Use only on a detail page when every hard constraint and required variant has explicit passing evidence.
- **Exclude:** Do not use with unknown constraints, stale price, unselected variants, or absent Buy Now control.
- **Input:** Final requirement checklist, evidence record, current price, selected variants, and clickables.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Confirm every hard constraint is pass and none is unknown.
2. Recheck current variant price and required option selections.
3. Confirm exact `Buy Now` text is currently clickable.
4. Produce a purchase-ready record; do not click until these checks pass.

## Verification and completion

Complete when the purchase-ready record lists evidence for identity, attributes, variants, and price.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If a check fails, route to the responsible verifier; if Buy Now is absent, stop rather than substituting another action.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass only a valid purchase-ready record to `webshop-purchase-executor`.

## References

- Read [Trajectory Example](references/trajectory_example.md) only when detailed patterns or examples are needed.
