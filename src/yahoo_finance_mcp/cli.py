import sys

from yahoo_finance_mcp.server import _get_quote


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: price TICKER", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1]
    try:
        quote = _get_quote(ticker)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(f"{quote['ticker']}: ${quote['price']:.2f} {quote['currency']}")


if __name__ == "__main__":
    main()
