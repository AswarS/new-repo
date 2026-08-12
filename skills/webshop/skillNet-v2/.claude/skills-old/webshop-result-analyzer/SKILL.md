---
name: webshop-result-analyzer
description: Extract and compare visible candidates on one WebShop result page. Use when the observation is a result page containing multiple product IDs and visible metadata. Do not use on a detail page, do not claim hidden attributes are satisfied, and do not execute purchase.
---

# webshop-result-analyzer

## Operating contract

- **Use when:** Use when the observation is a result page containing multiple product IDs and visible metadata.
- **Exclude:** Do not use on a detail page, do not claim hidden attributes are satisfied, and do not execute purchase.
- **Input:** Requirement record and the current result-page observation.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Extract each visible product ID, title, displayed price or range, and rating if relevant.
2. Reject visible hard-constraint violations; mark nonvisible attributes as unknown.
3. Rank remaining candidates by product identity, visible hard-attribute evidence, then preferences.
4. Return the best candidate with passed, failed, and unknown constraints.

## Verification and completion

Complete only when the selected ID is visible and no visible evidence contradicts a hard constraint.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If no candidate survives, return `no_candidate` with reasons; do not invent IDs or repeatedly rescan the same page.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass a candidate to `webshop-product-selector`; pass `no_candidate` to pagination or search refinement.

## References

- Read [Attribute Patterns](references/attribute_patterns.md) only when detailed patterns or examples are needed.
- Read [Execution Example](references/execution_example.md) only when detailed patterns or examples are needed.
