# WebShop query-format guide

Construct plain keyword queries:

- retain product identity;
- retain discriminative hard attributes;
- remove stop words and duplicate terms;
- separate terms with single spaces;
- omit price comparisons unless price is part of the product name;
- avoid commas, `<`, `>`, Boolean operators, and quotes.

Example:

`product=high heel`, `size=5`, `color=patent-beige`, `price<90`

→ `search[size 5 patent-beige high heel]`

The price remains in the requirement record for result/detail verification.
