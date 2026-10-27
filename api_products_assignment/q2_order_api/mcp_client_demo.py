"""Tiny MCP client: launches mcp_server.py over stdio, lists tools, calls order_api."""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    env = {"ORDER_API_BASE": os.environ.get("ORDER_API_BASE", "http://localhost:8000/api/orders")}
    params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"], env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            print("SCHEMA:", json.dumps(tools.tools[0].inputSchema, indent=2))
            for args in [
                {"action": "create_order", "item": "Laptop", "quantity": 2},
                {"action": "create_order", "item": "Mouse", "quantity": 0},
                {"action": "get_order", "order_id": 1},
                {"action": "get_order", "order_id": 99},
                {"action": "list_orders"},
            ]:
                res = await s.call_tool("order_api", args)
                print(f"\nCALL {args}\n ->", res.content[0].text)

asyncio.run(main())
