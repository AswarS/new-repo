---
name: webshop-product-detail-navigator
description: Open one selected product and classify its detail-page controls for downstream inspection. Use when a verified candidate ID is visible on a result page and its detail page is not yet open. Do not rank candidates, select variants, verify hidden attributes, or purchase.
---

# webshop-product-detail-navigator

## Operating contract

- **Use when:** Use when a verified candidate ID is visible on a result page and its detail page is not yet open.
- **Exclude:** Do not rank candidates, select variants, verify hidden attributes, or purchase.
- **Input:** Selected product ID, unresolved-constraint checklist, and current clickables.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Confirm the ID is the selected candidate and is currently clickable.
2. Emit one `click[product_id]` action.
3. On the returned page identify price, detail tabs, variant groups, Buy Now, and Back to Search controls.

## Verification and completion

Complete only when the returned page corresponds to the selected product and its controls are recorded.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If navigation fails or opens a different product, return to the result page once; do not repeat the same click on unchanged state.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass page controls and unresolved constraints to `webshop-product-detail-inspector`.

## References

- Read [Action Protocol](references/action_protocol.md) only when detailed patterns or examples are needed.
