"""Order REST API (Flask, in-memory)."""
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)
_orders = {}
_next_id = 1
_lock = threading.Lock()


def err(msg, code):
    return jsonify({"error": msg}), code


@app.post("/orders")
def create_order():
    global _next_id
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Body must be a JSON object", 400)
    item, qty = data.get("item"), data.get("quantity")
    if not isinstance(item, str) or not item.strip():
        return err("'item' must be a non-empty string", 400)
    if isinstance(qty, bool) or not isinstance(qty, int):
        return err("'quantity' must be an integer", 400)
    if qty <= 0:
        return err("'quantity' must be greater than 0", 422)
    with _lock:
        order = {"id": _next_id, "item": item, "quantity": qty, "status": "created"}
        _orders[_next_id] = order
        _next_id += 1
    return jsonify(order), 201


@app.get("/orders/<int:order_id>")
def get_order(order_id):
    order = _orders.get(order_id)
    return (jsonify(order), 200) if order else err(f"Order {order_id} not found", 404)


@app.get("/orders")
def list_orders():
    return jsonify(list(_orders.values())), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
