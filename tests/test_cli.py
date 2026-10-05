from unittest.mock import patch

import pytest

from yahoo_finance_mcp.cli import main


def test_main_prints_price_for_valid_ticker(capsys):
    quote = {
        "ticker": "AAPL",
        "price": 173.5,
        "currency": "USD",
        "change": 2.0,
        "change_percent": 1.17,
        "open": 171.5,
        "day_high": 174.0,
        "day_low": 171.0,
        "volume": 1_200_000,
        "as_of": "2026-10-03T00:00:00",
    }

    with patch("yahoo_finance_mcp.cli._get_quote", return_value=quote) as mock_get_quote:
        with patch("sys.argv", ["price", "aapl"]):
            main()

    mock_get_quote.assert_called_once_with("aapl")
    assert capsys.readouterr().out == "AAPL: $173.50 USD\n"


def test_main_exits_nonzero_with_usage_when_no_ticker_given(capsys):
    with patch("sys.argv", ["price"]):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    assert "Usage: price TICKER" in capsys.readouterr().err


def test_main_exits_nonzero_with_error_for_unknown_ticker(capsys):
    with patch(
        "yahoo_finance_mcp.cli._get_quote",
        side_effect=ValueError("No data found for ticker 'ZZZZ' — check that the symbol is correct."),
    ):
        with patch("sys.argv", ["price", "ZZZZ"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 1
    assert "No data found for ticker 'ZZZZ'" in capsys.readouterr().err
