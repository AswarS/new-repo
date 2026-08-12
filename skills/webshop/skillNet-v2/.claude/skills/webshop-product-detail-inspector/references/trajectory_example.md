# Detail-inspection example

User requires an easy-to-clean jewelry box with 10 slots under $60.

1. On the detail page, record current price `$20.97`; price passes.
2. Record “easy to clean” as unknown if the visible page provides no evidence.
3. Record `10 slots` as an available but unselected option.
4. Hand the required option to the option-selection skill.
5. After `10 slots` is selected, re-read the page and verify the selected state and price.
6. If “easy to clean” still lacks evidence, inspect one relevant Description or Features tab.
7. Return a pass/fail/unknown evidence record to `webshop-product-detail-check`.

This inspection skill never buys directly. Purchase is allowed only after the downstream
detail check confirms every hard constraint.
