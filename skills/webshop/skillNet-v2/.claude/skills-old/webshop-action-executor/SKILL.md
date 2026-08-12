---
name: webshop-action-executor
description: Format and emit one already-decided WebShop action using an exact currently available target. Use only after another skill or the current reasoning has selected one exact search term or clickable value. Do not use to choose a product, infer a variant, verify constraints, or plan multiple actions.
---

# webshop-action-executor

## Operating contract

- **Use when:** Use only after another skill or the current reasoning has selected one exact search term or clickable value.
- **Exclude:** Do not use to choose a product, infer a variant, verify constraints, or plan multiple actions.
- **Input:** The current observation and one selected target that is visible or a validated search query.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Classify the target as a search query or clickable value.
2. Confirm a click target appears exactly in the current observation; preserve its case and spacing.
3. Emit exactly one `search[keywords]` or `click[value]` action.

## Verification and completion

Complete only when the emitted command has balanced brackets and its click value exactly matches a current clickable.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If the target is absent or ambiguous, emit no guessed action and hand back to the selecting skill with the missing target.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Return the next observation to the skill responsible for interpreting the resulting page.
