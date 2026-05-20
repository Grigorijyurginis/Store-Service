_PRODUCT = {
    "name": "Widget Pro",
    "sku": "WGT-001",
    "category": "electronics",
    "price": 29.99,
    "stock_quantity": 100,
}


async def _create(client, overrides: dict | None = None) -> dict:
    resp = await client.post("/products", json={**_PRODUCT, **(overrides or {})})
    assert resp.status_code == 201
    return resp.json()


async def test_create_product(client):
    data = await _create(client)
    assert data["sku"] == _PRODUCT["sku"]
    assert data["price"] == _PRODUCT["price"]
    assert "id" in data


async def test_create_duplicate_sku_returns_409(client):
    await _create(client)
    resp = await client.post("/products", json=_PRODUCT)
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "conflict"


async def test_list_products_empty(client):
    resp = await client.get("/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_products(client):
    await _create(client)
    resp = await client.get("/products")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_get_product(client):
    product = await _create(client)
    resp = await client.get(f"/products/{product['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == product["id"]


async def test_get_product_not_found(client):
    resp = await client.get("/products/99999")
    assert resp.status_code == 404


async def test_update_product_price(client):
    product = await _create(client)
    resp = await client.put(f"/products/{product['id']}", json={"price": 49.99})
    assert resp.status_code == 200
    assert resp.json()["price"] == 49.99


async def test_update_product_not_found(client):
    resp = await client.put("/products/99999", json={"price": 10.0})
    assert resp.status_code == 404


async def test_delete_product(client):
    product = await _create(client)
    assert (await client.delete(f"/products/{product['id']}")).status_code == 204
    assert (await client.get(f"/products/{product['id']}")).status_code == 404


async def test_delete_product_not_found(client):
    resp = await client.delete("/products/99999")
    assert resp.status_code == 404


async def test_filter_by_category(client):
    await _create(client)
    await _create(client, {"sku": "BK-001", "category": "books"})
    resp = await client.get("/products?category=electronics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "electronics"


async def test_filter_in_stock(client):
    await _create(client)
    await _create(client, {"sku": "OUT-001", "stock_quantity": 0})
    resp = await client.get("/products?in_stock=true")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert all(i["stock_quantity"] > 0 for i in items)


async def test_pagination(client):
    for i in range(5):
        await _create(client, {"sku": f"SKU-{i:03d}"})
    resp = await client.get("/products?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
