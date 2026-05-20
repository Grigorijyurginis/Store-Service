import pytest

_PRODUCT = {
    "name": "Test Book",
    "sku": "BK-TEST-001",
    "category": "books",
    "price": 12.50,
    "stock_quantity": 20,
}


async def _make_product(client, overrides: dict | None = None) -> dict:
    resp = await client.post("/products", json={**_PRODUCT, **(overrides or {})})
    assert resp.status_code == 201
    return resp.json()


async def _make_order(client, product_id: int, qty: int = 1, customer: str = "cust-1"):
    return await client.post(
        "/orders",
        json={"customer_id": customer, "items": [{"product_id": product_id, "quantity": qty}]},
    )


async def test_create_order(client):
    p = await _make_product(client)
    resp = await _make_order(client, p["id"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["customer_id"] == "cust-1"
    assert data["total_amount"] == pytest.approx(_PRODUCT["price"])


async def test_create_order_decrements_stock(client):
    p = await _make_product(client)
    await _make_order(client, p["id"], qty=3)
    updated = (await client.get(f"/products/{p['id']}")).json()
    assert updated["stock_quantity"] == _PRODUCT["stock_quantity"] - 3


async def test_create_order_insufficient_stock(client):
    p = await _make_product(client)
    resp = await _make_order(client, p["id"], qty=9999)
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error"] == "insufficient_stock"
    assert detail["details"]["product_id"] == p["id"]
    assert detail["details"]["requested"] == 9999
    assert detail["details"]["available"] == _PRODUCT["stock_quantity"]


async def test_create_order_product_not_found(client):
    resp = await _make_order(client, product_id=99999)
    assert resp.status_code == 404


async def test_get_order(client):
    p = await _make_product(client)
    order_id = (await _make_order(client, p["id"])).json()["id"]
    resp = await client.get(f"/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


async def test_get_order_not_found(client):
    resp = await client.get("/orders/99999")
    assert resp.status_code == 404


async def test_list_orders(client):
    p = await _make_product(client)
    await _make_order(client, p["id"])
    resp = await client.get("/orders")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


async def test_status_transition_pending_to_confirmed(client):
    p = await _make_product(client)
    order_id = (await _make_order(client, p["id"])).json()["id"]
    resp = await client.patch(f"/orders/{order_id}/status", json={"status": "confirmed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


async def test_status_transition_full_pipeline(client):
    p = await _make_product(client)
    order_id = (await _make_order(client, p["id"])).json()["id"]
    for status in ("confirmed", "processing", "shipped", "delivered"):
        resp = await client.patch(f"/orders/{order_id}/status", json={"status": status})
        assert resp.status_code == 200
        assert resp.json()["status"] == status


async def test_status_transition_invalid(client):
    p = await _make_product(client)
    order_id = (await _make_order(client, p["id"])).json()["id"]
    # pending → shipped skips steps — must be rejected
    resp = await client.patch(f"/orders/{order_id}/status", json={"status": "shipped"})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error"] == "invalid_transition"
    assert detail["details"]["current"] == "pending"
    assert detail["details"]["target"] == "shipped"


async def test_cancel_order_restores_stock(client):
    p = await _make_product(client)
    initial_stock = p["stock_quantity"]
    order_id = (await _make_order(client, p["id"], qty=5)).json()["id"]
    resp = await client.delete(f"/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    updated = (await client.get(f"/products/{p['id']}")).json()
    assert updated["stock_quantity"] == initial_stock


async def test_cancel_delivered_order_returns_409(client):
    p = await _make_product(client)
    order_id = (await _make_order(client, p["id"])).json()["id"]
    for status in ("confirmed", "processing", "shipped", "delivered"):
        await client.patch(f"/orders/{order_id}/status", json={"status": status})
    resp = await client.delete(f"/orders/{order_id}")
    assert resp.status_code == 409
