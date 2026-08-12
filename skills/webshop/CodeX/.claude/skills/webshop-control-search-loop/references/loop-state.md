# Search Loop State

Maintain this compact scratch state:

```text
q=1/3 page=1 next_run=0
visited={ASIN: rejection_reason}
obs_sig=<page type + page number + first/last visible ASIN>
changed=<one query decision>
```

## Material query changes

Valid changes:

- replace one feature with a common synonym;
- remove one soft or low-information term;
- add a missing brand, model, compatibility, dimension, or pack token;
- correct a category noun after observing systematic category drift.

Invalid changes:

- capitalization or word-order only;
- adding price prose such as `under $40`;
- alternating two previous queries;
- quoting the same phrase;
- issuing the same search from a results page.

## Page decisions

- Many same-category results, no exact candidate: inspect the highest match, then paginate.
- Mostly unrelated categories: refine immediately.
- A candidate was rejected on a hard constraint: record it and choose an unseen ASIN.
- No new ASINs after navigation: stop that direction.
