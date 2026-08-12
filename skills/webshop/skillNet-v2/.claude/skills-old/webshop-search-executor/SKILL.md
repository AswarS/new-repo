---
name: webshop-search-executor
description: Execute one prepared search action and classify the returned page for the next stage. Use when a validated, non-duplicate query is ready and the current page exposes search. Do not formulate requirements, select products, or search again before inspecting the returned observation.
---

# webshop-search-executor

## Operating contract

- **Use when:** Use when a validated, non-duplicate query is ready and the current page exposes search.
- **Exclude:** Do not formulate requirements, select products, or search again before inspecting the returned observation.
- **Input:** One validated query, current observation, and attempted-query history.
- **Output:** Produce one stage result or one WebShop action. Never emit multiple interface actions in one turn.

## Workflow

1. Confirm search is available and the query is not in the attempt history.
2. Emit exactly one `search[keywords]` action.
3. On the next turn classify the outcome as useful results, zero results, irrelevant results, or environment error.

## Verification and completion

Complete when one action was issued and the returned outcome is recorded before any retry.

Do not treat missing evidence as a pass. Re-read the observation after every interface action before deciding the next action.

## Recovery and stopping

For zero/irrelevant results, hand off once to the formulator with evidence; for an environment error retry once, then stop.

Never repeat the same action from an unchanged observation. Preserve hard constraints during every retry or handoff.

## Handoff

Send useful results to a result-analysis skill; send failed outcomes to `webshop-search-formulator`.

## References

- Read [Action Grammar](references/action_grammar.md) only when detailed patterns or examples are needed.
