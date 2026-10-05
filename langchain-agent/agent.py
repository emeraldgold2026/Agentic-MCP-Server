import asyncio
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

MCP_SERVER_DIR = Path(__file__).resolve().parent.parent

MODEL = "openai:gpt-5.5"

QUESTION = "What's AAPL trading at right now, and how does that compare to MSFT?"


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "yahoo-finance": {
                "command": "uv",
                "args": ["run", "--directory", str(MCP_SERVER_DIR), "yahoo-finance-mcp"],
                "transport": "stdio",
            }
        }
    )

    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools from yahoo-finance-mcp: {[t.name for t in tools]}\n")

    agent = create_agent(
        model=MODEL,
        tools=tools,
        system_prompt="You are a helpful financial assistant. Use the available tools to answer questions about stock prices.",
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": QUESTION}]})

    print("--- Full message trace ---")
    for message in result["messages"]:
        message.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
