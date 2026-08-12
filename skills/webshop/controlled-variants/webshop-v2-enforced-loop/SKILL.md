---
name: webshop-v2-enforced-loop
description: Complete WebShop shopping tasks using the common workflow plus hard pre-action limits on repeated searches, pagination, candidate visits, and unchanged-state actions. Use to test whether enforceable loop control reduces redundant agent behavior.
---

# WebShop V2 Enforced Loop

## Experimental role

Use the common workflow with exactly one added mechanism: enforced search and action-loop limits. Do not add a structured constraint ledger, a general persistent execution-state record, or a required-option purchase gate beyond the common workflow.

## Output contract

- Emit exactly one executable WebShop action per turn.
- The final response must contain only `search[keywords]`, `click[value]`, or `[DONE]`.
- Keep counters and checks internal. Do not expose analysis, records, checklists, skill names, or multiple actions.
- Use only actions and clickable values supported by the current observation.

## Pre-action loop gate

Derive the following counts from the visible action/observation history before every action:

```text
distinct_queries
pages_seen_for_current_query
candidates_opened_for_current_query
same_action_on_same_observation
consecutive_unchanged_observations
remaining_steps
```

Forbid an action when any rule applies:

- The identical action already occurred on an equivalent observation.
- The query is identical to a prior query.
- Three materially distinct queries have already been attempted.
- Two result pages have already been examined for the current query.
- Two candidates have already been opened for the current query.
- Two consecutive actions produced an unchanged observation.
- Four or fewer steps remain and the action starts broad exploration rather than completing the best current path.

Each query revision must change exactly one retrieval decision. Do not perform cosmetic rewording. Do not immediately reverse `Next` with `Prev`, or `Prev` with `Next`, unless returning to one specifically identified candidate.

## Common workflow

1. Read the instruction and issue one concise search using product identity and useful descriptive terms.
2. Apply the loop gate before every search, page navigation, candidate click, return, or purchase.
3. On results, choose the best unseen plausible product rather than revisiting an inspected candidate.
4. On a product page, inspect visible title, price, options, Description, or Features as needed.
5. Select a visible option when the instruction clearly requests it.
6. Purchase the best current compliant candidate when `Buy Now` is visible.
7. Emit `[DONE]` after purchase confirmation.

## Common recovery

- If the loop gate forbids an action, choose a different action class: inspect one unseen candidate, inspect one relevant evidence tab, make one materially different query, or complete the best current path.
- When a detail tab hides `Buy Now`, return once to the product page.
- Re-read the observation and recompute the loop gate after every action.

## Completion

Stop after purchase confirmation. If all permitted searches and candidates are exhausted, emit `[DONE]` rather than repeat a forbidden action.
