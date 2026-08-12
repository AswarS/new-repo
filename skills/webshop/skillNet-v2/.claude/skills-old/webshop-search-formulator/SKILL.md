---
name: webshop-search-formulator
description: Formulate one concise search query from parsed criteria while balancing precision and recall. Use after parsing when a query is needed, or when a failed query has an explicit refinement plan. Do not inspect result pages, choose products, or repeat an unchanged query.
---

# webshop-search-formulator

## Operating contract

- **Use when:** Use after parsing when a query is needed, or when a failed query has an explicit refinement plan.
- **Exclude:** Do not inspect result pages, choose products, or repeat an unchanged query.
- **Input:** Structured product type, hard attributes, preferences, and prior attempted queries if any.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Rank terms: product identity first, then discriminative hard attributes, then at most one useful preference.
2. Exclude non-searchable price syntax and verbose filler.
3. For refinement, change exactly one aspect: remove the least discriminative preference or add a missing identity synonym.
4. Return one lowercase space-separated `search[keywords]` action.

## Verification and completion

Reject an empty query, a query missing product identity, or any query already present in the attempt history.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

After two unsuccessful reformulations, stop reformulating and hand off with the attempted queries and observed failure.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Send the action to `webshop-search-executor`; send exhausted attempts to the controlling workflow.

## References

- Read [Search Strategy Guide](references/search_strategy_guide.md) only when detailed patterns or examples are needed.
