# Purchase Checkpoint

Before `Buy Now`, answer every item:

- [ ] Product identity/category is still correct.
- [ ] Every fixed hard constraint has explicit evidence.
- [ ] Every requested variant has been clicked and visibly confirmed.
- [ ] No unrequested default option remains for a required variant.
- [ ] Current price is visible and strictly below the limit.
- [ ] `Buy Now` is available.

After `Buy Now`:

- [ ] Confirmation contains `Thank you`, `Purchased`, or an order code.
- [ ] Purchased ASIN matches the verified candidate.
- [ ] Recorded options match the requested variants.
- [ ] Emit `[DONE]` and take no further action.

If any pre-purchase box cannot be checked, abort this candidate and return the exact missing evidence to the search loop.
