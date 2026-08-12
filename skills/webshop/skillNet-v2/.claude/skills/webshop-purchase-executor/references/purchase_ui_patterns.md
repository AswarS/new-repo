# WebShop purchase control

In this benchmark, execute purchase only through an exact currently visible `Buy Now`
clickable. Preserve its displayed case and spacing in `click[value]`.

Do not substitute `Add to Cart`, `Checkout`, subscription, rental, preorder, or localized
controls: they represent different flows and are outside this skill's scope.

Because purchase is irreversible, emit one click only after the purchase-ready gate passes.
If confirmation is absent, return failure for review and do not retry automatically.
