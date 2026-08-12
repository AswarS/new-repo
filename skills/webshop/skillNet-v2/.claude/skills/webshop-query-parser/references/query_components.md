# Query-component patterns

Use these patterns only to produce structured fields; do not execute search or click actions.

| Field | Examples |
|---|---|
| product | popcorn, high heel, jewelry box |
| hard attribute | gluten free, exact size, required material |
| preference | premium, top rated, easy to clean |
| quantity | 12 pack, 5 ounce, 1 gallon |
| variant | red, size 5, pack of 2 |
| brand | Nike, Kellogg's |

Preserve price semantics:

- `lower than X` → operator `<`, value `X`
- `at most X` → operator `<=`, value `X`
- `above X` → operator `>`, value `X`
- `at least X` → operator `>=`, value `X`
- `between X and Y` → explicit lower and upper bounds

Do not turn “around X” into an invented numeric tolerance. Record it as an approximate
preference unless the user defines an acceptable range.
