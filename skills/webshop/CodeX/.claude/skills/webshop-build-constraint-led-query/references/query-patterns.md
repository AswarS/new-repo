# Constraint and Query Patterns

| Instruction signal | Ledger placement | Query treatment |
|---|---|---|
| brand or model (`LG`, `L'Eau d'Issey`, `MN4`) | hard | Keep exact token in every query |
| compatibility (`for Apple`, `male to female`) | hard | Include identity plus compatibility |
| measurement (`20m`, `6.76 fl oz`, `12 inch`) | hard unless clearly an option | Keep normalized unit; try exact form first |
| pack/count (`pack of 2`, `six pack`) | hard | Include count or pack phrase |
| dietary/safety (`gluten free`, `BPA free`) | hard | Include rare property; verify on detail page |
| color/size/style shown as a selector | variant | Search by identity plus rare color/style, then select in-page |
| quality language (`great`, `high quality`) | soft | Omit from initial query |
| “lower than X” | price | Do not search as prose; enforce strict `< X` before purchase |

Prefer discriminative nouns over broad adjectives. For example:

- `LG blu-ray home theater remote control`, not `remote control`.
- `20m 4g lte coaxial cable male female`, not `high quality digital cable`.
- `himalayan black rock salt 2.8 ounce`, not `gluten free salt`.

Fallback queries must change retrieval semantics. Capitalization changes, word reordering, quoting an unsupported search phrase, or adding `under $X` do not count as a new query.
