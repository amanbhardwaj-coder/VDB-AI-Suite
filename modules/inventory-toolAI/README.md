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

## Supabase preparation

The module is now ready to sync uploads, learned header knowledge, and run history to Supabase.

Expected secrets or environment variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET` default: `inventory-ai`
- `SUPABASE_RUNS_TABLE` default: `inventory_ai_runs`
- `SUPABASE_KNOWLEDGE_TABLE` default: `inventory_ai_learned_headers`

For Streamlit, use `.streamlit/secrets.toml` like:

```toml
[inventory_ai_supabase]
enabled = true
url = "https://YOUR_PROJECT.supabase.co"
service_role_key = "YOUR_SERVICE_ROLE_KEY"
storage_bucket = "inventory-ai"
runs_table = "inventory_ai_runs"
knowledge_table = "inventory_ai_learned_headers"
```

Database bootstrap SQL is in `configs/supabase_schema.sql`.

Secrets example is in `configs/secrets.toml.example`.

## OpenAI copilot

The inventory AI tool can optionally use the OpenAI Responses API for:

- requirement gathering
- follow-up question generation
- mapping-fix suggestions

Configure Streamlit secrets with:

```toml
[openai]
enabled = true
api_key = "YOUR_OPENAI_API_KEY"
model = "gpt-5"
```

## Recommended setup order

1. Create a Supabase project.
2. Create a private storage bucket named `inventory-ai` or your chosen bucket.
3. Run `configs/supabase_schema.sql` in the Supabase SQL editor.
4. Copy `configs/secrets.toml.example` into `.streamlit/secrets.toml` and fill in your real values.
5. Start the app and use the `Supabase Admin` panel in the sidebar to test the connection and refresh knowledge.
