# Yahoo Finance MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stdio MCP server, backed by `yfinance`, that exposes four tools for Yahoo Finance stock data: latest quote, batch quotes, historical OHLCV bars, and basic company info.

**Architecture:** A single FastMCP server (`mcp.server.fastmcp.FastMCP`) with one module, `server.py`. Each MCP tool is a thin async wrapper that runs a synchronous `yfinance`-calling helper function via `asyncio.to_thread`, so the server's event loop never blocks on `yfinance`'s blocking HTTP calls. The sync helpers contain all the logic and are what the tests exercise directly.

**Tech Stack:** Python 3.10+, `uv` (packaging/venv), `mcp` SDK (FastMCP high-level API), `yfinance`, `pandas` (transitive via yfinance, also used directly in tests), `pytest`. Tests call the synchronous helper functions directly, not the `async` tool wrappers, so no `pytest-asyncio` is needed.

**Spec:** `docs/superpowers/specs/2026-10-04-yahoo-finance-mcp-design.md`

## Global Constraints

- Python >= 3.10.
- Project lives at the repo root (this repo is otherwise empty) and is managed with `uv` via `pyproject.toml`.
- MCP SDK: use the high-level `FastMCP` API, not the low-level `Server` API.
- Transport: stdio only.
- Every `yfinance`-calling helper is synchronous; every MCP tool function is `async` and calls its helper via `asyncio.to_thread(...)`.
- Unknown/invalid tickers must raise a `ValueError` with a clear message instead of returning empty/partial data. Exact messages are specified per-task below and must match exactly (tests assert on them).
- The batch tool (`get_stock_prices`) must isolate per-ticker failures — one bad ticker reports an error entry, it must not raise and abort the whole call.
- All non-live tests must run offline by mocking `yahoo_finance_mcp.server.yf.Ticker` — no real network calls in the default `pytest` run.
- Field names in tool return values are exact and must match across tasks: `ticker`, `price`, `currency`, `change`, `change_percent`, `open`, `day_high`, `day_low`, `volume`, `as_of` (quote); `date`, `open`, `high`, `low`, `close`, `volume` (historical bar); `name`, `sector`, `industry`, `market_cap`, `description` (company info).

---

## File Structure

```
pyproject.toml
README.md
src/yahoo_finance_mcp/
  __init__.py
  server.py
tests/
  __init__.py
  test_server.py
```

- `server.py` holds the `FastMCP` instance, the four tool functions, their sync helper functions, and `main()`. It's one file because the four tools share the same small surface (all thin wrappers over `yfinance.Ticker`) — splitting now would be premature; if more tools are added later, split helpers into their own module then.
- `test_server.py` holds all unit tests, grouped by tool, plus the skipped-by-default live smoke test.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/yahoo_finance_mcp/__init__.py`
- Create: `src/yahoo_finance_mcp/server.py`
- Create: `tests/__init__.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Produces: a `mcp` module-level `FastMCP` instance in `yahoo_finance_mcp.server`, and a `main()` function that later tasks and the console-script entry point rely on.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "yahoo-finance-mcp"
version = "0.1.0"
description = "MCP server exposing Yahoo Finance stock data via yfinance"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.2.0",
    "yfinance>=0.2.40",
]

[project.scripts]
yahoo-finance-mcp = "yahoo_finance_mcp.server:main"

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pandas>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/yahoo_finance_mcp"]
```

- [ ] **Step 2: Create the package skeleton**

Create `src/yahoo_finance_mcp/__init__.py` (empty file).

Create `src/yahoo_finance_mcp/server.py`:

```python
import asyncio

import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("yahoo-finance")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

Create `tests/__init__.py` (empty file).

- [ ] **Step 3: Write the failing scaffolding test**

Create `tests/test_server.py`:

```python
from yahoo_finance_mcp.server import main, mcp


def test_server_is_named_yahoo_finance():
    assert mcp.name == "yahoo-finance"


def test_main_is_callable():
    assert callable(main)
```

- [ ] **Step 4: Install dependencies and run the test**

Run: `uv sync`
Run: `uv run pytest tests/test_server.py -v`

Expected: both tests PASS (this task has no real "failing first" step since there's no logic yet to get wrong — scaffolding is verified by successful import and the two assertions above).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/yahoo_finance_mcp/__init__.py src/yahoo_finance_mcp/server.py tests/__init__.py tests/test_server.py
git commit -m "chore: scaffold yahoo-finance-mcp project with uv and FastMCP"
```

---

## Task 2: `get_stock_price` tool

**Files:**
- Modify: `src/yahoo_finance_mcp/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `mcp` (FastMCP instance from Task 1).
- Produces: `_get_quote(ticker: str) -> dict` and the `get_stock_price` MCP tool — later tasks (3) call `_get_quote` directly.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_server.py`:

```python
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from yahoo_finance_mcp.server import _get_quote


def _make_history_df(rows):
    index = pd.to_datetime([row["date"] for row in rows])
    return pd.DataFrame(
        {
            "Open": [row["open"] for row in rows],
            "High": [row["high"] for row in rows],
            "Low": [row["low"] for row in rows],
            "Close": [row["close"] for row in rows],
            "Volume": [row["volume"] for row in rows],
        },
        index=index,
    )


def test_get_quote_returns_latest_price_and_context():
    history_df = _make_history_df(
        [
            {"date": "2026-10-02", "open": 170.0, "high": 172.0, "low": 169.0, "close": 171.0, "volume": 1_000_000},
            {"date": "2026-10-03", "open": 171.5, "high": 174.0, "low": 171.0, "close": 173.0, "volume": 1_200_000},
        ]
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = history_df
    mock_ticker.fast_info = {"currency": "USD"}

    with patch("yahoo_finance_mcp.server.yf.Ticker", return_value=mock_ticker) as mock_cls:
        result = _get_quote("aapl")

    mock_cls.assert_called_once_with("aapl")
    mock_ticker.history.assert_called_once_with(period="2d")
    assert result == {
        "ticker": "AAPL",
        "price": 173.0,
        "currency": "USD",
        "change": 2.0,
        "change_percent": pytest.approx((2.0 / 171.0) * 100),
        "open": 171.5,
        "day_high": 174.0,
        "day_low": 171.0,
        "volume": 1_200_000,
        "as_of": history_df.index[-1].to_pydatetime().isoformat(),
    }


def test_get_quote_raises_for_unknown_ticker():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("yahoo_finance_mcp.server.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(ValueError, match="No data found for ticker 'zzzz'"):
            _get_quote("zzzz")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL with `ImportError: cannot import name '_get_quote'`

- [ ] **Step 3: Implement `_get_quote` and the `get_stock_price` tool**

In `src/yahoo_finance_mcp/server.py`, add after the `mcp = FastMCP("yahoo-finance")` line:

```python
def _get_quote(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="2d")
    if hist.empty:
        raise ValueError(f"No data found for ticker '{ticker}' — check that the symbol is correct.")

    last = hist.iloc[-1]
    prev_close = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(last["Open"])
    price = float(last["Close"])
    change = price - prev_close
    change_percent = (change / prev_close * 100) if prev_close else 0.0

    try:
        currency = t.fast_info["currency"]
    except (KeyError, TypeError):
        currency = "USD"

    return {
        "ticker": ticker.upper(),
        "price": price,
        "currency": currency,
        "change": change,
        "change_percent": change_percent,
        "open": float(last["Open"]),
        "day_high": float(last["High"]),
        "day_low": float(last["Low"]),
        "volume": int(last["Volume"]),
        "as_of": hist.index[-1].to_pydatetime().isoformat(),
    }


@mcp.tool()
async def get_stock_price(ticker: str) -> dict:
    """Get the latest price and daily trading context for a stock ticker."""
    return await asyncio.to_thread(_get_quote, ticker)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yahoo_finance_mcp/server.py tests/test_server.py
git commit -m "feat: add get_stock_price tool"
```

---

## Task 3: `get_stock_prices` batch tool

**Files:**
- Modify: `src/yahoo_finance_mcp/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `_get_quote(ticker: str) -> dict` (Task 2).
- Produces: `_get_quotes(tickers: list[str]) -> list[dict]` and the `get_stock_prices` MCP tool.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_server.py`:

```python
from yahoo_finance_mcp.server import _get_quotes


def test_get_quotes_reports_per_ticker_errors():
    good_df = _make_history_df(
        [
            {"date": "2026-10-02", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 500_000},
            {"date": "2026-10-03", "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.5, "volume": 600_000},
        ]
    )
    good_ticker = MagicMock()
    good_ticker.history.return_value = good_df
    good_ticker.fast_info = {"currency": "USD"}

    bad_ticker = MagicMock()
    bad_ticker.history.return_value = pd.DataFrame()

    def ticker_factory(symbol):
        return good_ticker if symbol == "GOOD" else bad_ticker

    with patch("yahoo_finance_mcp.server.yf.Ticker", side_effect=ticker_factory):
        results = _get_quotes(["GOOD", "BAD"])

    assert results[0]["ticker"] == "GOOD"
    assert results[0]["price"] == 101.5
    assert results[1] == {
        "ticker": "BAD",
        "error": "No data found for ticker 'BAD' — check that the symbol is correct.",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL with `ImportError: cannot import name '_get_quotes'`

- [ ] **Step 3: Implement `_get_quotes` and the `get_stock_prices` tool**

In `src/yahoo_finance_mcp/server.py`, add after `get_stock_price`:

```python
def _get_quotes(tickers: list[str]) -> list[dict]:
    results = []
    for ticker in tickers:
        try:
            results.append(_get_quote(ticker))
        except Exception as exc:
            results.append({"ticker": ticker.upper(), "error": str(exc)})
    return results


@mcp.tool()
async def get_stock_prices(tickers: list[str]) -> list[dict]:
    """Get the latest price and daily trading context for multiple stock tickers."""
    return await asyncio.to_thread(_get_quotes, tickers)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yahoo_finance_mcp/server.py tests/test_server.py
git commit -m "feat: add get_stock_prices batch tool"
```

---

## Task 4: `get_historical_prices` tool

**Files:**
- Modify: `src/yahoo_finance_mcp/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `mcp` (FastMCP instance from Task 1).
- Produces: `_get_history(ticker: str, period: str, interval: str) -> dict` and the `get_historical_prices` MCP tool.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_server.py`:

```python
from yahoo_finance_mcp.server import _get_history


def test_get_history_returns_bars():
    history_df = _make_history_df(
        [
            {"date": "2026-09-01", "open": 150.0, "high": 152.0, "low": 149.0, "close": 151.0, "volume": 800_000},
            {"date": "2026-09-02", "open": 151.0, "high": 153.0, "low": 150.5, "close": 152.5, "volume": 900_000},
        ]
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = history_df

    with patch("yahoo_finance_mcp.server.yf.Ticker", return_value=mock_ticker) as mock_cls:
        result = _get_history("msft", period="5d", interval="1d")

    mock_cls.assert_called_once_with("msft")
    mock_ticker.history.assert_called_once_with(period="5d", interval="1d")
    assert result["ticker"] == "MSFT"
    assert result["period"] == "5d"
    assert result["interval"] == "1d"
    assert result["bars"] == [
        {
            "date": history_df.index[0].to_pydatetime().isoformat(),
            "open": 150.0,
            "high": 152.0,
            "low": 149.0,
            "close": 151.0,
            "volume": 800_000,
        },
        {
            "date": history_df.index[1].to_pydatetime().isoformat(),
            "open": 151.0,
            "high": 153.0,
            "low": 150.5,
            "close": 152.5,
            "volume": 900_000,
        },
    ]


def test_get_history_raises_for_unknown_ticker():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("yahoo_finance_mcp.server.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(
            ValueError,
            match="No historical data found for ticker 'zzzz' with period='1mo', interval='1d'",
        ):
            _get_history("zzzz", period="1mo", interval="1d")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL with `ImportError: cannot import name '_get_history'`

- [ ] **Step 3: Implement `_get_history` and the `get_historical_prices` tool**

In `src/yahoo_finance_mcp/server.py`, add after `get_stock_prices`:

```python
def _get_history(ticker: str, period: str, interval: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period=period, interval=interval)
    if hist.empty:
        raise ValueError(
            f"No historical data found for ticker '{ticker}' with period='{period}', interval='{interval}'."
        )

    bars = [
        {
            "date": index.to_pydatetime().isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
        }
        for index, row in hist.iterrows()
    ]

    return {
        "ticker": ticker.upper(),
        "period": period,
        "interval": interval,
        "bars": bars,
    }


@mcp.tool()
async def get_historical_prices(ticker: str, period: str = "1mo", interval: str = "1d") -> dict:
    """Get historical OHLCV price bars for a stock ticker.

    period and interval are passed straight through to yfinance, e.g.
    period in 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max and
    interval in 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo.
    """
    return await asyncio.to_thread(_get_history, ticker, period, interval)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yahoo_finance_mcp/server.py tests/test_server.py
git commit -m "feat: add get_historical_prices tool"
```

---

## Task 5: `get_company_info` tool

**Files:**
- Modify: `src/yahoo_finance_mcp/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `mcp` (FastMCP instance from Task 1).
- Produces: `_get_company_info(ticker: str) -> dict` and the `get_company_info` MCP tool.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_server.py`:

```python
from yahoo_finance_mcp.server import _get_company_info


def test_get_company_info_returns_fields():
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "marketCap": 2_800_000_000_000,
        "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones.",
    }

    with patch("yahoo_finance_mcp.server.yf.Ticker", return_value=mock_ticker) as mock_cls:
        result = _get_company_info("aapl")

    mock_cls.assert_called_once_with("aapl")
    assert result == {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 2_800_000_000_000,
        "description": "Apple Inc. designs, manufactures, and markets smartphones.",
    }


def test_get_company_info_raises_for_missing_info():
    mock_ticker = MagicMock()
    mock_ticker.info = {}

    with patch("yahoo_finance_mcp.server.yf.Ticker", return_value=mock_ticker):
        with pytest.raises(ValueError, match="No company info found for ticker 'zzzz'"):
            _get_company_info("zzzz")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL with `ImportError: cannot import name '_get_company_info'`

- [ ] **Step 3: Implement `_get_company_info` and the `get_company_info` tool**

In `src/yahoo_finance_mcp/server.py`, add after `get_historical_prices`:

```python
def _get_company_info(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.info
    if not info or not info.get("longName"):
        raise ValueError(f"No company info found for ticker '{ticker}' — check that the symbol is correct.")

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "description": info.get("longBusinessSummary"),
    }


@mcp.tool()
async def get_company_info(ticker: str) -> dict:
    """Get basic company info (name, sector, industry, market cap, description) for a stock ticker."""
    return await asyncio.to_thread(_get_company_info, ticker)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yahoo_finance_mcp/server.py tests/test_server.py
git commit -m "feat: add get_company_info tool"
```

---

## Task 6: Live smoke test, README, and manual run check

**Files:**
- Create: `README.md`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `_get_quote` (Task 2), `main()` (Task 1).
- Produces: nothing consumed by later tasks (this is the last task).

- [ ] **Step 1: Add the skipped-by-default live smoke test**

Append to `tests/test_server.py`:

```python
import os


@pytest.mark.skipif(
    not os.environ.get("YF_MCP_LIVE_TEST"),
    reason="hits real Yahoo Finance data; set YF_MCP_LIVE_TEST=1 to run",
)
def test_get_quote_live_smoke():
    result = _get_quote("AAPL")
    assert result["ticker"] == "AAPL"
    assert result["price"] > 0
```

- [ ] **Step 2: Run the full default test suite and confirm the smoke test is skipped**

Run: `uv run pytest tests/test_server.py -v`
Expected: all previous tests PASS, `test_get_quote_live_smoke` reports SKIPPED

- [ ] **Step 3: Run the live smoke test manually against real data**

Run: `YF_MCP_LIVE_TEST=1 uv run pytest tests/test_server.py::test_get_quote_live_smoke -v`
Expected: PASS (requires network access; confirms the real `yfinance` integration still works end to end)

- [ ] **Step 4: Write `README.md`**

```markdown
# yahoo-finance-mcp

An MCP server exposing Yahoo Finance stock data (via the `yfinance`
library) as four tools: `get_stock_price`, `get_stock_prices`,
`get_historical_prices`, and `get_company_info`.

## Setup

    uv sync

## Run standalone (stdio)

    uv run yahoo-finance-mcp

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
```

- [ ] **Step 5: Manually verify the server starts over stdio**

Run: `uv run yahoo-finance-mcp` then send Ctrl+C after confirming it starts without a traceback (a bare stdio MCP server blocks waiting for a client; there is no banner to check beyond "no immediate crash").

- [ ] **Step 6: Commit**

```bash
git add README.md tests/test_server.py
git commit -m "docs: add README and live smoke test"
```
