---
name: webshop-result-filter
description: Filter visible result-page candidates using hard constraints without treating missing evidence as a pass. Use after result extraction when multiple listings must be reduced to a viable shortlist. Do not use on detail pages, do not select the first item by default, and do not verify hidden features from title absence.
---

# webshop-result-filter

## Operating contract

- **Use when:** Use after result extraction when multiple listings must be reduced to a viable shortlist.
- **Exclude:** Do not use on detail pages, do not select the first item by default, and do not verify hidden features from title absence.
- **Input:** Structured requirements and extracted visible candidate fields.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Apply product identity and visible hard constraints first.
2. Classify each constraint as pass, fail, or unknown for each candidate.
3. Reject any candidate with a hard fail; retain unknowns for detail inspection.
4. Rank survivors by number and importance of hard passes, then preferences and price.

## Verification and completion

Complete with a shortlist whose entries include evidence and unresolved constraints; an empty shortlist is valid.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

If empty, paginate once when an unseen next page exists; otherwise request one distinct query refinement and stop.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Pass the shortlist to `webshop-product-selector` or the empty result to navigation/refinement.

## References

- Read [Constraint Extraction Guide](references/constraint_extraction_guide.md) only when detailed patterns or examples are needed.
