---
name: webshop-v4-option-gate
description: Complete WebShop shopping tasks using the common workflow plus an explicit required-option checklist that blocks purchase until requested color, size, style, flavor, quantity, or other variants are selected and verified. Use to test the effect of option completeness on agent reward.
---

# WebShop V4 Option Gate

## Experimental role

Use the common workflow with exactly one added mechanism: a required-option checklist and hard purchase gate. Do not add a structured fixed-constraint ledger, numerical search-loop limits, or a general persistent execution-state record beyond option tracking.

## Output contract

- Emit exactly one executable WebShop action per turn.
- The final response must contain only `search[keywords]`, `click[value]`, or `[DONE]`.
- Keep the option checklist internal. Do not expose analysis, records, checklists, skill names, or multiple actions.
- Use only actions and clickable values supported by the current observation.

## Required-option checklist

On a product page, internally construct:

```text
required_options: option group and exact requested value
available_options: visible group and values
selected_options: confirmed or previously clicked group and value
missing_options: required values not selected
current_price: visible price after the latest selection
```

Apply these rules:

- Treat requested color, size, style, scent, flavor, capacity, quantity, and pack count as required options when matching selectors are visible.
- Match exact values or unambiguously equivalent formatting; do not substitute a near color, size, quantity, or style.
- Click one missing required option per turn in page order.
- After each option click, re-read the page and update selected options and current price.
- Do not click unspecified options merely because selectors are present.
- If an exact required option is absent, reject the candidate instead of choosing the nearest value.

## Purchase gate

`click[Buy Now]` is forbidden unless:

```text
missing_options is empty
every required option is selected or was explicitly clicked without an error
the current visible price satisfies the instruction
Buy Now is visible on the current page
```

After purchase, require a confirmation observation before emitting `[DONE]`.

## Common workflow

1. Read the instruction and issue one concise search using product identity and useful descriptive terms.
2. Choose a plausible visible product whose title and price do not contradict the instruction.
3. On the product page, construct the required-option checklist.
4. Select each missing required option exactly once and update the checklist.
5. Apply the purchase gate; buy only when it passes.
6. Emit `[DONE]` after purchase confirmation.

## Common recovery

- If a required option is unavailable, return to search and choose another candidate.
- If a detail tab hides `Buy Now`, return to the product page without clearing the option checklist.
- If an option action explicitly fails, retry once only when the exact label remains visible.

## Completion

Stop successfully only after all required options pass the gate and the environment confirms purchase.
