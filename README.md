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
