---
name: webshop-v3-explicit-state
description: Complete WebShop shopping tasks using the common workflow plus an explicit internal state record for stage, action history, candidates, unresolved requirements, and selected options. Use to test whether persistent state representation reduces repeated or inconsistent agent actions.
---

# WebShop V3 Explicit State

## Experimental role

Use the common workflow with exactly one added mechanism: an explicit execution-state record. Do not add a formal identity/hard/variant constraint ledger, numerical search-loop limits, or a required-option purchase gate beyond the common workflow.

## Output contract

- Emit exactly one executable WebShop action per turn.
- The final response must contain only `search[keywords]`, `click[value]`, or `[DONE]`.
- Keep state internal. Do not expose analysis, records, checklists, skill names, or multiple actions.
- Use only actions and clickable values supported by the current observation.

## Persistent execution state

Before every action, internally reconstruct and update:

```text
stage: START | SEARCH | RESULTS | PRODUCT_DETAIL | OPTION_SELECTION | BUY | DONE
attempted_queries: ordered list
visited_pages: ordered list
visited_candidates: ASIN with outcome
rejected_candidates: ASIN with reason
selected_options: option group to clicked value
unresolved_requirements: requirements still needing evidence or action
last_action: exact action
last_observation_changed: yes | no | unknown
```

Apply these rules:

- Choose only actions appropriate for the current stage.
- Never treat a rejected candidate as unseen.
- Never repeat a query, candidate click, or option click already recorded unless the observation explicitly reports failure.
- When an option click produces no visible change, retain the attempted selection in `selected_options`; retry only if the observation explicitly shows a different selected value or an error.
- Preserve unresolved requirements until visible evidence or an action resolves them.
- Update state only from the original instruction and visible history; do not invent hidden state.

## Common workflow

1. Initialize the execution state and issue one concise search using product identity and useful descriptive terms.
2. Update state after results and open one plausible unvisited candidate.
3. Record product evidence, rejection reasons, unresolved requirements, and visible options.
4. Select a requested option only when it is not already recorded in `selected_options`.
5. Purchase when the current state indicates a plausible product and `Buy Now` is visible.
6. Record purchase confirmation, set stage to DONE, and emit `[DONE]`.

## Common recovery

- Use `rejected_candidates` to avoid returning to known failures.
- Use `attempted_queries` to choose a genuinely different search when needed.
- Use `last_observation_changed` to switch action class after an ineffective action.
- When a detail tab hides `Buy Now`, record the navigation and return once to the product page.

## Completion

Stop only after the state is DONE or the recorded history shows no new executable path.
