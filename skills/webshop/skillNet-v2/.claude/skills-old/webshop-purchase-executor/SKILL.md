---
name: webshop-purchase-executor
description: Execute the single terminal Buy Now action from a valid purchase-ready record. Use only when the purchase gate has passed on the current unchanged detail page and Buy Now is visible. Do not verify products, select options, substitute Add to Cart, or purchase on partial/unknown evidence.
---

# webshop-purchase-executor

## Operating contract

- **Use when:** Use only when the purchase gate has passed on the current unchanged detail page and Buy Now is visible.
- **Exclude:** Do not verify products, select options, substitute Add to Cart, or purchase on partial/unknown evidence.
- **Input:** Current observation and a purchase-ready record tied to that observation.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Confirm the page and selected variants have not changed since the gate passed.
2. Confirm `Buy Now` exactly matches a current clickable.
3. Emit exactly one `click[Buy Now]` action.
4. Read the next observation and record whether purchase confirmation occurred.

## Verification and completion

Complete only when the environment returns a purchase confirmation or terminal success state.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If the click fails, retry once only when the observation proves a transient error and remains unchanged; otherwise stop without another purchase attempt.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Return terminal success, or a structured failure requiring human/controller review.

## References

- Read [Purchase Ui Patterns](references/purchase_ui_patterns.md) only when detailed patterns or examples are needed.
