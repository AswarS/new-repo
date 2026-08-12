# Option-selection strategy

Apply strategies in this order:

1. Satisfy explicit hard requirements such as size, quantity, pack count, and color.
2. Reject an option that violates a hard requirement even if it is cheaper or listed first.
3. Among equally compliant options, use an explicit user preference.
4. Only then use lower verified price as a tie-breaker.

Do not infer that the first option is cheapest. When an option's effect is unknown, select at
most one plausible compliant value, read the refreshed page, and verify its price and state.
If the effect remains unknown or no compliant value exists, reject the product.

For multiple option groups, select one value per turn and revalidate after every click.
