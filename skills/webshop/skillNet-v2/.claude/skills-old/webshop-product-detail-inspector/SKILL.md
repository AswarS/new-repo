---
name: webshop-product-detail-inspector
description: Collect explicit evidence for unresolved constraints from a product detail page. Use after opening a product when price, attributes, or variant requirements remain unknown. Do not use on result pages, infer missing facts, or purchase before verification is complete.
---

# webshop-product-detail-inspector

## Operating contract

- **Use when:** Use after opening a product when price, attributes, or variant requirements remain unknown.
- **Exclude:** Do not use on result pages, infer missing facts, or purchase before verification is complete.
- **Input:** Requirement checklist, current detail observation, and visited detail tabs.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Check visible title, price, options, and specification text against every hard constraint.
2. Open at most one unvisited Description or Features tab when required evidence is missing.
3. Classify each hard constraint as pass, fail, or unknown with page evidence.
4. Return a verification record and any required variant selections.

## Verification and completion

Complete when every hard constraint is pass/fail/unknown and no visible contradiction is ignored.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

Reject on any hard fail. If evidence remains unavailable after one relevant detail tab, reject or mark unverifiable; never loop across tabs.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass selectable requirements to an option skill, or the completed record to `webshop-product-detail-check`.

## References

- Read [Action Guidelines](references/action_guidelines.md) only when detailed patterns or examples are needed.
- Read [Trajectory Example](references/trajectory_example.md) only when detailed patterns or examples are needed.
