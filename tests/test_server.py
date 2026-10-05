from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from yahoo_finance_mcp.server import _get_quote, main, mcp


def test_server_is_named_yahoo_finance():
    assert mcp.name == "yahoo-finance"


def test_main_is_callable():
    assert callable(main)


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
