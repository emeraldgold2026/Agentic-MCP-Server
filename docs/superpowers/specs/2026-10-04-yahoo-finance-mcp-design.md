# Yahoo Finance MCP Server — Design

Date: 2026-10-04

## Purpose

Build an MCP server that exposes stock market data sourced from Yahoo
Finance (via the unofficial `yfinance` Python library) as a set of MCP
tools, so any MCP client (Claude Code, Claude Desktop, etc.) can look up
ticker prices, historical series, and basic company info in conversation.

## Scope

In scope:
- A new standalone Python project, `yahoo-finance-mcp`, living in this
  repo.
- Four MCP tools (below), all backed by `yfinance`.
- stdio transport only.
- Unit tests that mock `yfinance.Ticker` so the suite doesn't depend on
  network access or Yahoo's live data.

Out of scope (YAGNI for this iteration):
- HTTP/SSE transport or any remote hosting.
- Authentication/authorization (stdio servers run locally under the
  launching client's identity).
- Caching, rate limiting, or retry/backoff policies.
- Any provider other than Yahoo Finance via `yfinance`.
- Options chains, dividends/splits, fundamentals beyond the basic
  company info fields listed below.

## Why `yfinance`

Yahoo Finance has no official, documented public API. `yfinance` is the
most widely used community library wrapping Yahoo's undocumented
endpoints (chart/quote data, history, basic info). It is unofficial and
can break if Yahoo changes its endpoints — acceptable for this project's
purpose; not a concern to design around further.

## Tech stack

- **Language**: Python (3.10+)
- **MCP SDK**: official `mcp` Python SDK, high-level `FastMCP` API
  (`mcp.server.fastmcp.FastMCP`) — tools are plain functions with type
  hints and docstrings; the SDK derives the JSON schema and handles
  protocol plumbing. Chosen over the low-level `Server` API to avoid
  hand-writing schemas for four simple tools.
- **Data source**: `yfinance` (pip/uv package)
- **Packaging/tooling**: `uv`, with `pyproject.toml`
- **Transport**: stdio

## Project layout

This repo (`Agentic-MCP-Server`) is otherwise empty, so the project
lives at the repo root rather than in a nested subdirectory — the tree
below is rooted at the repo root itself:

```
pyproject.toml
  README.md
  src/yahoo_finance_mcp/
    __init__.py
    server.py        # FastMCP instance + tool definitions
  tests/
    test_server.py
```

## Tools

All tools run their underlying `yfinance` call inside
`asyncio.to_thread(...)` since `yfinance` performs blocking HTTP calls
under the hood (via `requests`), and FastMCP tool handlers are async.

### 1. `get_stock_price(ticker: str)`

Returns the latest quote for a single ticker:
- `ticker` (echoed back, uppercased)
- `price` (latest/regular market price)
- `currency`
- `change` (absolute day change)
- `change_percent`
- `open`, `day_high`, `day_low`
- `volume`
- `as_of` (timestamp of the quote, ISO 8601)

### 2. `get_stock_prices(tickers: list[str])`

Batch version of (1). Returns a list of per-ticker results, each either
the same shape as `get_stock_price`'s result or an `{ "ticker": ..., "error": "..." }`
entry. One bad ticker in the batch must not fail the whole call —
failures are isolated per ticker.

### 3. `get_historical_prices(ticker: str, period: str = "1mo", interval: str = "1d")`

Returns an OHLCV series for the given ticker:
- `ticker`
- `period`, `interval` (echoed back)
- `bars`: list of `{ date, open, high, low, close, volume }`

`period` and `interval` are passed straight through to
`yfinance.Ticker.history(period=..., interval=...)`, so they accept the
same values `yfinance` does (e.g. `period` in `1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max`;
`interval` in `1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo`). No extra
validation layer — invalid combinations surface as a tool error from
whatever `yfinance`/Yahoo rejects.

### 4. `get_company_info(ticker: str)`

Returns basic descriptive info for a ticker:
- `ticker`
- `name` (long name)
- `sector`
- `industry`
- `market_cap`
- `description` (long business summary)

## Error handling

- **Unknown/invalid ticker**: `yfinance` returns empty data (empty
  `history()` DataFrame, or an `info`/`fast_info` dict missing expected
  keys) rather than raising. Each tool must detect this condition and
  raise an MCP tool error with a clear message, e.g.
  `"No data found for ticker 'XYZ' — check that the symbol is correct."`,
  instead of returning empty/garbage fields.
- **Network/HTTP errors**: let the underlying exception propagate as an
  MCP tool error; no custom retry logic.
- **Batch tool (`get_stock_prices`)**: per-ticker errors are caught and
  reported inline in that ticker's result entry rather than aborting the
  batch.

## Testing

- Unit tests in `tests/test_server.py` mock `yfinance.Ticker` (e.g. via
  `unittest.mock.patch`) to return canned data, so the suite runs
  offline and deterministically. Cover: a normal single-ticker lookup,
  an unknown ticker (error path), a mixed-success batch, and historical
  data shaping.
- One live smoke test hitting real Yahoo data, marked to be skipped by
  default (e.g. `@pytest.mark.skip` or gated behind an env var), useful
  for manual sanity-checking but not part of the default `pytest` run.

## Running / integration

- Local dev: `uv run yahoo-finance-mcp` (stdio).
- Claude Desktop / Claude Code config: a standard stdio MCP server
  entry pointing at the `uv run` (or installed console-script) command.
- `README.md` documents setup (`uv sync`), running standalone, and the
  config snippet for adding it to an MCP client.
