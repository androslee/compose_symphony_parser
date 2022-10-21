# Symphony Rules Notes

Expressed in EDN (a subset of Clojure syntax), not too different from JSON. Examples below have been translated to JSON.

## Root

Data available (other than :symphony):

Depending on how you fetch, this data will not be available and will skip straight to the root node.

```json
{
  ":uid": "sdfadfddasf", // text
  ":capital": 10000,
  ":apply-taf-fee?": true, // ?
  ":symphony-benchmarks": [],
  ":slippage-percent": 0.0005, // this is 5 basis points
  ":client-commit": "bvcxdfff", // ?
  ":apply-reg-fee?": true, // ?
  ":ticker-benchmarks": [
    // benchmarks section for comparison
    {
      ":color": "#F6609F",
      ":id": "SPY",
      ":checked?": true,
      ":type": ":ticker",
      ":ticker": "SPY"
    }
  ]
}
```

## Tree

Inside `":symphony"` is a tree. The top layer is the root node.

- descendants are under `":children"`, this is a list of nodes.
- the current node's type is `":step"`.
- the node's unique identifier is the `":id"` field. Unclear if this changes.

## Node Types

`:root`: the first node under `:symphony`.

```json
{
  // these first 3 are common to all nodes (:children is optional, left blank for brevity)
  // will not be repeated for other examples in this doc.
  ":id": "43refdscxz",
  ":step": ":root",
  ":children": [],

  ":name": "farm fun 99",
  ":description": "",
  ":rebalance": ":daily" // other values currently unknown
}
```

`:wt-cash-equal` and `:wt-cash-specified`: weight all children equally. Children will have :weight attribute, which has :num and :den (numberator and denominator).

`:if`: all children are of type `:if-child`.

`:if-child`: if condition is met, 100% of weight passes to children (not other sibling nodes).

May be an `else` block, which only triggers if all other sibling `:if-child` conditions are false.

A **condition** is made of 2 **values** (which may be _fixed_ or an _indicator_) and a **comparison** (like `<`).
One **value** is called the left-hand-side value (lhs for shot), the other is the right-hand-side (rhs). The logic for these differs slightly. Only the right-hand-side can be a fixed value.
