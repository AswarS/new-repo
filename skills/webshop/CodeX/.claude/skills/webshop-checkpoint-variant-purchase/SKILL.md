---
name: webshop-checkpoint-variant-purchase
description: Select required WebShop product variants exactly once, verify the resulting state and price, and commit a purchase only after a final constraint checkpoint. Use after a candidate passes fixed-attribute verification and before Buy Now.
---

# Checkpoint Variant and Purchase

## Condition

Apply only after `webshop-gate-candidate-evidence` returns `PASS_TO_VARIANTS`.

## Policy

1. List every required variant from the original ledger in page order.
2. For each variant, click the exact visible option once. Match normalized case and spacing, but preserve meaningful punctuation, dimensions, and model codes.
3. After each click, verify that the observation changed or that the option is visibly selected. If neither is true, retry once only when the action label is unambiguous.
4. Never cycle through options to “test” them. Never substitute a near color, size, style, quantity, scent, or flavor.
5. After all selections, rerun the candidate evidence gate for:
   - exact selected values;
   - product identity and fixed constraints;
   - updated price under the strict limit;
   - availability of `Buy Now`.
6. Click `Buy Now` exactly once only if the final checkpoint passes.
7. After purchase, require a confirmation observation such as `Thank you`, `Purchased`, or an order code. Then emit `[DONE]`.

Read [references/purchase-checklist.md](references/purchase-checklist.md) before acting when there are multiple selectors or variant-dependent prices.

## Termination

Stop without purchase if an exact required option is absent, selection does not persist after one retry, price fails or remains unknown, a fixed constraint becomes contradictory, or `Buy Now` is unavailable.

Stop successfully only after purchase confirmation is visible and `[DONE]` is emitted.

## Result

Return one of:

```text
PURCHASED <ASIN> options={<name>: <value>, ...} price=<value>
```

```text
ABORTED <ASIN> reason=<missing option | unconfirmed selection | price | constraint | unavailable>
```

Do not report success merely because `Buy Now` was clicked.
