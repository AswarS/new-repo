# Evidence Rules

## Strong evidence

- Exact tokens in title for category, brand, model, size, quantity, or compatibility.
- Explicit statements in Description or Features.
- An exact requested value among visible variant options.
- A numeric visible price.

## Weak or invalid evidence

- Search-query wording repeated in the instruction.
- A related product category.
- Generic adjectives such as “premium” standing in for a concrete property.
- An option name without selecting it.
- Rating or review sentiment standing in for a required feature.

## Truncated observations

Use only visible text. If a hard property is cut off, open the most likely evidence tab once. If still absent after the two-tab budget, mark it `UNKNOWN` and reject. Do not infer hidden facts from a plausible title.

## Price

- “lower than 40” requires price `< 40.00`; `$40.00` fails.
- Recheck after variant selection because variant price may differ.
- If price is unavailable, retain `UNKNOWN`; do not buy.
