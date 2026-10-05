import asyncio

import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("yahoo-finance")


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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
