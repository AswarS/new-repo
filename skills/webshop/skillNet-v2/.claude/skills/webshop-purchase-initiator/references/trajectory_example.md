# Purchase-gate example

User requires whitening toothpaste that freshens breath under $40.

Before handoff, record:

- product identity and both required features: pass with visible evidence;
- current selected option: pass;
- current price `$17.99 < $40`: pass;
- `Buy Now`: visible.

Produce a purchase-ready record containing these checks. Do not click in this skill. Pass the
record and unchanged observation to `webshop-purchase-executor`, which owns the terminal
`click[Buy Now]` action.
