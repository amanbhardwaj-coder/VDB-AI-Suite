# AI Inventory Studio V3.1 Rules Fix

This bundle fixes the issue where Generated Rules JSON was empty.

## Why it was empty

The previous parser only recognized a very narrow instruction pattern.
If the text did not exactly match that pattern, the JSON remained:

{
  "pricing_rules": [],
  "normalization_rules": [],
  "variant_rules": []
}

## What changed

Updated:
- agents/rule_parser.py
- agents/ai_analyzer.py
- core/expander.py

Now instructions like this work:

"14k metal prices should be 500 and rest should be 1000"

Generated JSON will include:

{
  "pricing_rules": [
    {
      "type": "metal_price_rule",
      "price": 500,
      "else_price": 1000
    }
  ]
}

It also supports:
- create variants only for metal and shape
- keep jewelry style static
- remove duplicate tokens
- normalize separators

The pricing rule is applied during Create Inventory.
