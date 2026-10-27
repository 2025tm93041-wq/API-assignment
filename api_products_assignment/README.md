# SE*ZG504 API-based Products – EC-1 Assignment

Folder layout
```
q1_grpc/            task.proto, server.py, client.py, requirements.txt
q2_order_api/       app.py, mcp_server.py, mcp_client_demo.py, tool_schema.json,
                    kong/kong.yml, docker-compose.yml, Dockerfile, test_rate_limit.sh
q3_rate_limiters/   rate_limiters.py, test_rate_limiters.py
```
Prerequisites: Python 3.10+, Docker Desktop (for Kong), curl.

---------------------------------------------------------------------
## QUESTION 1 – gRPC Task Manager
```bash
cd q1_grpc
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. task.proto
```
**Terminal A (server, with 2-second delay on GetTask so the timeout demo works):**
`python server.py --delay 2`   *(for a normal run use `python server.py`)*

**Terminal B (client):**
1. `python client.py`            -> create x3, get #2, ListTasks stream, bidi updates
2. `python client.py --errors`  -> INVALID_ARGUMENT / NOT_FOUND / FAILED_PRECONDITION
3. `python client.py --timeout` -> 1s deadline vs 2s server sleep -> DEADLINE_EXCEEDED handled gracefully

Screenshots: (1) protoc command + generated files; (2) server running; (3) client main flow output;
(4) error cases output; (5) timeout output + server log "GetTask sleeping 2s".
Tip: restart the server without `--delay` and re-run `python client.py --timeout` to show the success path.

---------------------------------------------------------------------
## QUESTION 2 – Order API + MCP + Kong
### Part A – API (direct test)
```bash
cd q2_order_api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py                       # http://localhost:5000
curl -X POST localhost:5000/orders -H "Content-Type: application/json" -d '{"item":"Laptop","quantity":2}'
curl localhost:5000/orders/1
curl localhost:5000/orders
curl -X POST localhost:5000/orders -H "Content-Type: application/json" -d '{"item":"Pen","quantity":0}'   # 422
curl localhost:5000/orders/99                                                                             # 404
```
Stop `python app.py` (Ctrl+C) before the next step – Docker runs the API on the same port.

### Part C – Kong
```bash
docker compose up --build -d
curl http://localhost:8001/services          # Kong Admin API: order-service
curl http://localhost:8001/routes            # route /api/orders
curl http://localhost:8001/plugins           # rate-limiting, minute=5
curl -i http://localhost:8000/api/orders     # through Kong; note X-RateLimit-* headers
./test_rate_limit.sh                         # 8 requests: first 5 -> 200, rest -> 429
```
Windows PowerShell:
`1..8 | % { curl.exe -s -o NUL -w "Request $_ -> %{http_code}`n" http://localhost:8000/api/orders }`

`kong/kong.yml` is the declarative config (your "Kong configuration" deliverable). Kong runs DB-less, so
the Admin API is read-only – use it only to show the loaded config. Wait ~1 minute for the window to reset
before re-testing. Note: the demo script's first request count includes any earlier calls in the same minute.

### Part B – MCP server
```bash
python mcp_client_demo.py     # starts mcp_server.py over stdio; calls order_api through Kong
```
Prints the tool list, JSON input schema, and results for create/get/list + validation errors.
Bypass Kong: `ORDER_API_BASE=http://localhost:5000/orders python mcp_client_demo.py`.
Rate limit via MCP: call `list_orders` 6+ times quickly -> tool returns `http_status: 429`.

Use with a real LLM client (Claude Desktop) – add to `claude_desktop_config.json`:
```json
{ "mcpServers": { "order-api": {
    "command": "python", "args": ["/FULL/PATH/q2_order_api/mcp_server.py"],
    "env": { "ORDER_API_BASE": "http://localhost:8000/api/orders" } } } }
```
Then ask: "Create an order for 3 keyboards, then list all orders."

Flow: LLM -> MCP client -> mcp_server.py -> Kong (:8000/api/orders) -> Order API (:5000/orders)

Screenshots: API curl tests; `docker compose ps`; Admin API service/route/plugin output; 429 output;
MCP demo output (schema + calls); optional Claude Desktop screenshot.
Deliverable 3 (MCP tool schema) = `tool_schema.json` (also printed by the demo).

---------------------------------------------------------------------
## QUESTION 3 – Rate limiting algorithms
```bash
cd q3_rate_limiters
python rate_limiters.py          # side-by-side demo
python test_rate_limiters.py     # unit tests
```
* **Token Bucket** – tokens refill at a constant rate up to capacity; each request consumes a token.
  Allows bursts up to capacity, then limits to the refill rate.
* **Leaky Bucket** – requests fill a bucket draining at a constant rate; overflow is rejected (meter variant)
  or queued and released at a fixed rate (`LeakyBucketQueue`). Smooths traffic.
* Key difference: token bucket permits bursts; leaky bucket enforces steady output.

---------------------------------------------------------------------
## Final submission checklist
1. PDF report: per question -> brief explanation, code snippets, commands, screenshots.
2. ZIP: report PDF + the three folders + this README.
