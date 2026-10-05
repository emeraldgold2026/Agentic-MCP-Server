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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
