# Candidate evaluation logic

Parse each visible listing into product ID, title, current visible price, and other visible
metadata. For every user constraint assign one state:

- `pass`: visible evidence supports it;
- `fail`: visible evidence contradicts it;
- `unknown`: the result page does not expose enough evidence.

Reject candidates with any hard `fail`. Do not reject a candidate merely because a hard
attribute is absent from its title; retain it as `unknown` for detail inspection.

Rank survivors by:

1. product-identity match;
2. number and importance of hard passes;
3. fewer unknown hard constraints;
4. preferences;
5. lower visible price as a final tie-breaker.

If none survive, return no recommendation and request bounded pagination or query refinement.
