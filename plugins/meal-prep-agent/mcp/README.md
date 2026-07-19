# Woolworths MCP (Python)

An unofficial Python 3.12 MCP server for Woolworths Australia, built with
FastMCP and Pydantic. It ports the tools from
[`elijah-g/Woolworths-mcp`](https://github.com/elijah-g/Woolworths-mcp) and
incorporates pull request 2's resilient endpoint discovery, compact responses,
delivery information, and fulfilment selection.

## Tools

- Browser/session: `woolworths_open_browser`, `woolworths_navigate`,
  `woolworths_get_cookies`, `woolworths_close_browser`
- Catalogue: `woolworths_search_products`,
  `woolworths_get_product_details`, `woolworths_get_specials`,
  `woolworths_get_categories`
- Trolley: `woolworths_add_to_cart`, `woolworths_get_cart`,
  `woolworths_remove_from_cart`, `woolworths_update_cart_quantity`
- Delivery: `woolworths_get_delivery_info`, `woolworths_set_fulfilment`

All tool inputs and structured outputs are validated Pydantic models. API
responses are deliberately slimmed before returning them to an MCP client.

## Install

Python 3.12 is required. With `uv`:

```bash
uv venv --python 3.12
uv pip install -e .
uv run playwright install chromium
```

Or with a Python 3.12 environment and pip:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/playwright install chromium
```

The browser download is required for session capture and automatic endpoint
discovery. On Linux, `playwright install --with-deps chromium` may be needed.

## Run

Run the installed stdio server:

```bash
woolworths-mcp
```

Or run it through FastMCP:

```bash
fastmcp run src/woolworths_mcp/server.py:mcp
```

Example MCP client configuration after installing into `.venv`:

```json
{
  "mcpServers": {
    "woolworths": {
      "command": "/absolute/path/to/woolworths-mcp/.venv/bin/woolworths-mcp"
    }
  }
}
```

Typical workflow:

1. Call `woolworths_open_browser` with `{"request": {"headless": false}}`.
2. Sign in in the opened browser if required.
3. Call `woolworths_get_cookies`.
4. Use catalogue, trolley, or delivery tools.
5. Call `woolworths_close_browser`; captured cookies remain available until
   the MCP process exits.

Mutation tools change the active Woolworths trolley or fulfilment state. This
project is unofficial and is not affiliated with Woolworths Group Limited.
Use it in accordance with Woolworths' terms and applicable law.

## Development

```bash
uv sync --extra dev --python 3.12
uv run ruff check .
uv run mypy
uv run pytest
```

Endpoint recovery first tries known API path migrations, then observes
Woolworths browser network requests as a last resort. Validated discoveries are
cached in the platform user-cache directory, not in the project checkout.
