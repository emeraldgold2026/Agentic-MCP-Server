# yahoo-finance-mcp

An MCP server exposing Yahoo Finance stock data (via the `yfinance`
library) as four tools: `get_stock_price`, `get_stock_prices`,
`get_historical_prices`, and `get_company_info`.

## Setup

    uv sync

## Run standalone (stdio)

    uv run yahoo-finance-mcp

## Get a single ticker's price from the command line

    uv run price TICKER

e.g. `uv run price AAPL` prints `AAPL: $173.50 USD`.

## Run the tests

    uv run pytest

The default test run is fully offline (mocks `yfinance`). To also run
the live smoke test against real Yahoo Finance data:

    YF_MCP_LIVE_TEST=1 uv run pytest tests/test_server.py::test_get_quote_live_smoke

## Add to an MCP client (e.g. Claude Code / Claude Desktop)

Add a stdio server entry pointing at this project, e.g.:

```json
{
  "mcpServers": {
    "yahoo-finance": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/yahoo-finance-mcp", "yahoo-finance-mcp"]
    }
  }
}
```

## Tools

- `get_stock_price(ticker)` — latest price, currency, day change/%, open/high/low, volume, timestamp.
- `get_stock_prices(tickers)` — batch version; per-ticker errors are reported inline instead of failing the whole call.
- `get_historical_prices(ticker, period="1mo", interval="1d")` — OHLCV bars; `period`/`interval` accept the same values `yfinance` does.
- `get_company_info(ticker)` — name, sector, industry, market cap, description.

## Project history

### Original prompts

The two prompts that kicked off each half of this project:

- **MCP server:** "Can you build a mcp server tool using yahoo finance api to get the latest stock prices for a given ticker"
- **LangChain agent:** "Create a custom MCP Server with tools, test it with MCP inspector tool locally, and then these use local mcp server with Langchain"

### Key decisions

**MCP server (`yahoo-finance-mcp`):**

- Python 3.10+, managed with `uv` (`pyproject.toml` + `uv.lock`, no `requirements.txt`).
- Data source: `yfinance` — Yahoo Finance has no official public API; `yfinance` is the standard unofficial library for it.
- Built on the MCP SDK's high-level `FastMCP` API rather than the low-level `Server` API, to avoid hand-writing JSON schemas for simple tools.
- `mcp` pinned to `>=1.2.0,<2` after discovering `mcp` 2.x renamed `FastMCP` to `MCPServer`, which would've broken this server's code.
- stdio transport only — no HTTP/SSE, no auth; matches how local MCP clients (Claude Desktop, Claude Code, the Inspector) already connect.
- Four tools scoped up front: `get_stock_price`, `get_stock_prices` (batch, isolates per-ticker errors instead of failing the whole call), `get_historical_prices`, `get_company_info`.
- Quote responses return price plus daily trading context (change, change %, open/high/low, volume), not just a bare number.
- Project files live at the repo root rather than a nested subdirectory, since this repo was otherwise empty.
- `uv.lock` is committed for reproducible installs.
- Added a `price` CLI command (`uv run price TICKER`) for a quick one-ticker lookup without going through an MCP client.
- All four tools' return types were unified to `dict[str, Any]` so every tool produces consistent `structuredContent`, after an inconsistency surfaced during review (one tool returned `list[dict]`, the others `dict`, giving mismatched output schemas).
- Verified live against the official MCP Inspector (`npx @modelcontextprotocol/inspector --cli ...`), exercising all four tools including error paths (invalid ticker, mixed-batch failure).

**LangChain agent (`langchain-agent/`):**

- Kept as its own separate `uv` project rather than folding into the server's package — following LangChain's own convention of not mixing a demo/consumer script into the library it consumes.
- Connects to the MCP server via `langchain-mcp-adapters`' `MultiServerMCPClient`, which spawns `uv run --directory <repo-root> yahoo-finance-mcp` as a stdio subprocess — the same connection style Claude Desktop and the Inspector use.
- Model: started with Anthropic (`anthropic:claude-sonnet-5`), later switched to OpenAI (`openai:gpt-5.5`) on request — demonstrating LangChain's model-agnostic `create_agent(model, tools)` API.
- API key is read from a local `langchain-agent/.env` file (gitignored) via `python-dotenv`, rather than pasted into chat or hardcoded.
- The script evolved from a fixed demo question ("What's AAPL trading at... vs MSFT?") to an interactive `input()` prompt that asks the user for a ticker symbol at runtime.
