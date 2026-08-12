---
name: webshop-product-evaluator
description: Evaluate visible candidate evidence and recommend one product for detail inspection. Use on a result page after requirements are known and candidates have been extracted. Do not purchase, infer hidden specifications, or choose a candidate with a visible hard failure.
---

# webshop-product-evaluator

## Operating contract

- **Use when:** Use on a result page after requirements are known and candidates have been extracted.
- **Exclude:** Do not purchase, infer hidden specifications, or choose a candidate with a visible hard failure.
- **Input:** Requirement record and candidate evidence from the current page.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Score hard-constraint evidence before preferences.
2. Treat missing attributes as unknown requiring detail inspection, not as failure or success.
3. Choose the highest-evidence candidate; break ties by fewer unknown hard constraints, then lower price.
4. Return one candidate ID and the constraints to verify on its detail page.

## Verification and completion

The recommendation is valid only when its ID is clickable and the rationale identifies every visible hard pass/fail/unknown.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If all candidates hard-fail, return no recommendation and hand off to pagination or query refinement.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the recommendation to `webshop-product-selector`.

## References

- Read [Evaluation Logic](references/evaluation_logic.md) only when detailed patterns or examples are needed.
