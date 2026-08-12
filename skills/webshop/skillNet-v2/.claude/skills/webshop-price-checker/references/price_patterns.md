# Price patterns

Recognize current selling prices such as `$164.95`, `Price: $164.95`, and `$1,299.99`.
Ignore crossed-out list prices when a current price is explicitly shown.

Preserve the user's operator:

- `lower than`, `under`, `less than`: strict `<`
- `at most`, `no more than`: `<=`
- `above`, `more than`: strict `>`
- `at least`: `>=`

Do not compare a range before choosing a variant. After any variant selection, use the
refreshed current price. If price or currency cannot be determined, return `unknown` and
block purchase. Perform the arithmetic directly; no helper script is required.
