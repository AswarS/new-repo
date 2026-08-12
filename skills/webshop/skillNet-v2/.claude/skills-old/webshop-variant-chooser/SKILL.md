---
name: webshop-variant-chooser
description: Choose a size, quantity, color, or pack variant that satisfies the requirement record. Use when a product detail page exposes multiple variants and at least one variant decision remains. Do not use when no variant is required, on result pages, or to apply an arbitrary default that changes a hard quantity/size constraint.
---

# webshop-variant-chooser

## Operating contract

- **Use when:** Use when a product detail page exposes multiple variants and at least one variant decision remains.
- **Exclude:** Do not use when no variant is required, on result pages, or to apply an arbitrary default that changes a hard quantity/size constraint.
- **Input:** Variant group, clickable values, explicit requirements, current selection, and price.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Map explicit size/quantity/color requirements to an exact available value.
2. When unspecified, choose a standard single-unit option only if it preserves all hard constraints.
3. Emit one click and re-read the updated page.
4. Verify selection and new price before another variant or purchase action.

## Verification and completion

Complete when every required variant is visibly selected and current price passes.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If no compliant variant exists, reject the product. If the selected state does not change, do not repeat the click.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass verified variants to the detail checker.

## References

- Read [Trajectory](references/trajectory.md) only when detailed patterns or examples are needed.
