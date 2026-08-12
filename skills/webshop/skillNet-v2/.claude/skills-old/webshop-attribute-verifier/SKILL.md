---
name: webshop-attribute-verifier
description: Verify one or more required product attributes against explicit detail-page evidence. Use when a detail-page checklist contains unresolved attribute, price, size, material, or color constraints. Do not use on result pages, treat title absence as proof of failure, or buy within the same turn as option selection.
---

# webshop-attribute-verifier

## Operating contract

- **Use when:** Use when a detail-page checklist contains unresolved attribute, price, size, material, or color constraints.
- **Exclude:** Do not use on result pages, treat title absence as proof of failure, or buy within the same turn as option selection.
- **Input:** Hard-constraint checklist, current page evidence, option state, and clickables.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Compare the current variant price with the exact user operator and bound.
2. For each attribute record pass, fail, or unknown and cite visible evidence.
3. If a required option is available but unselected, request one exact option click.
4. After the page refresh, reverify price and option state before declaring pass.

## Verification and completion

Complete only when all hard attributes are evidenced and the current selected state is confirmed.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

On hard fail return to search; on unavailable evidence inspect one relevant tab, then reject as unverifiable rather than guessing.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass verified state to the detail checker or required option to `webshop-attribute-selector`.
