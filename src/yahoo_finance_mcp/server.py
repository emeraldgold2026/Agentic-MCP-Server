import asyncio

import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("yahoo-finance")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
