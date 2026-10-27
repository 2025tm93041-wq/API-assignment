"""MCP server exposing ONE tool `order_api` with three actions.

Flow: LLM -> MCP client -> this server -> Kong (http://localhost:8000/api/orders) -> Order API
Override the target with:  ORDER_API_BASE=http://localhost:5000/orders  (bypass Kong)
"""
import os
from typing import Literal, Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE = os.environ.get("ORDER_API_BASE", "http://localhost:8000/api/orders").rstrip("/")
mcp = FastMCP("order-mcp-server")


@mcp.tool(name="order_api",
          description="Manage orders. action=create_order needs item+quantity; "
                      "action=get_order needs order_id; action=list_orders needs nothing.")
def order_api(
    action: Literal["create_order", "get_order", "list_orders"],
    item: Optional[str] = None,
    quantity: Optional[int] = None,
    order_id: Optional[int] = None,
) -> dict:
    # ---- schema / business input validation -----------------------------
    if action == "create_order":
        if not item or not item.strip():
            return {"error": "create_order requires non-empty 'item'"}
        if quantity is None or quantity <= 0:
            return {"error": "create_order requires integer 'quantity' > 0"}
    elif action == "get_order":
        if order_id is None or order_id < 1:
            return {"error": "get_order requires 'order_id' >= 1"}

    # ---- route to the correct endpoint ----------------------------------
    try:
        with httpx.Client(timeout=10) as c:
            if action == "create_order":
                r = c.post(BASE, json={"item": item, "quantity": quantity})
            elif action == "get_order":
                r = c.get(f"{BASE}/{order_id}")
            else:
                r = c.get(BASE)
    except httpx.HTTPError as e:
        return {"error": f"Upstream unreachable: {e}"}

    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text}
    # Return the API's JSON response (with HTTP status for transparency, e.g. 429 from Kong)
    return {"http_status": r.status_code, "response": body}


if __name__ == "__main__":
    mcp.run(transport="stdio")
