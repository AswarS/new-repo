---
name: webshop-product-selector
description: Click one already-evaluated candidate to open its detail page. Use when a ranked shortlist exists and the top candidate ID is visible and clickable. Do not use to rank raw results, guess a product ID, or buy directly from the result page.
---

# webshop-product-selector

## Operating contract

- **Use when:** Use when a ranked shortlist exists and the top candidate ID is visible and clickable.
- **Exclude:** Do not use to rank raw results, guess a product ID, or buy directly from the result page.
- **Input:** Top candidate ID, its evidence, unresolved constraints, and current clickables.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Confirm the candidate has no known hard failure.
2. Confirm the exact product ID appears in current clickables.
3. Record unresolved constraints for detail verification.
4. Emit one `click[product_id]` action.

## Verification and completion

Complete only when the next observation is the selected product detail page.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If the ID is absent or navigation fails, do not repeat blindly; return to result analysis with the changed observation.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the detail page and unresolved checklist to `webshop-product-detail-check`.

## References

- Read [Action Format](references/action_format.md) only when detailed patterns or examples are needed.
