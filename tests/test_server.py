from yahoo_finance_mcp.server import main, mcp


def test_server_is_named_yahoo_finance():
    assert mcp.name == "yahoo-finance"


def test_main_is_callable():
    assert callable(main)
