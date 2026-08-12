---
name: webshop-gate-candidate-evidence
description: Evaluate a WebShop product against an explicit constraint ledger using page evidence and hard rejection gates. Use after opening a product, before selecting variants, and before treating a candidate as purchase-ready.
---

# Gate Candidate Evidence

## Condition

Apply whenever a product detail page is open and a constraint ledger is available.

## Policy

1. Confirm exact product identity and category from the title. Reject related-but-different products immediately.
2. Build one row per constraint with status `PASS`, `FAIL`, `SELECT`, or `UNKNOWN`.
3. Use evidence in this order: title and visible price, option labels, Description, Features. Open a detail tab only when it can resolve a hard `UNKNOWN`.
4. Interpret evidence conservatively:
   - synonyms may satisfy a feature only when meaning is equivalent;
   - absence is `UNKNOWN`, not `PASS`;
   - contradictory text is `FAIL`;
   - a visible option matching a requested value is `SELECT`.
5. Reject immediately on wrong identity/category, incompatible model, any explicit hard-attribute failure, or visible price at/above a strict upper bound.
6. Permit at most two evidence-tab clicks per candidate. Do not cycle among Description, Features, and Reviews.
7. Ignore reviews and ratings unless the instruction explicitly requires them.
8. Pass only when every hard fixed constraint is `PASS`, every required variant is `SELECT` or already selected, and current price passes.

Read [references/evidence-rules.md](references/evidence-rules.md) when evidence is truncated, conflicting, or expressed only as a selector.

## Termination

Stop on the first hard `FAIL`. Otherwise stop after all hard constraints are resolved or after two evidence tabs leave any hard constraint `UNKNOWN`.

## Result

Return:

```text
candidate: <ASIN>
identity: PASS|FAIL
constraints:
  - <constraint>: PASS|FAIL|SELECT|UNKNOWN — <page evidence>
price: PASS|FAIL|UNKNOWN — <visible value>
decision: PASS_TO_VARIANTS|REJECT
reason: <first failure or unresolved hard constraints>
```

Never click `Buy Now` from this skill.
