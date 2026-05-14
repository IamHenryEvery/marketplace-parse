async def test_list_requires_auth(client):
    resp = await client.get("/api/products")
    assert resp.status_code == 401


async def test_list_empty(user_client):
    resp = await user_client.get("/api/products")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_minimal(user_client):
    resp = await user_client.post(
        "/api/products",
        json={"name": "My product", "urls": []},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "My product"
    assert body["urls"] == []
    assert isinstance(body["product_id"], int)


async def test_create_with_urls(user_client, marketplace_id):
    resp = await user_client.post(
        "/api/products",
        json={
            "name": "With urls",
            "urls": [
                {"url": "https://example.com/a", "marketplace_id": marketplace_id},
                {"url": "https://example.com/b", "marketplace_id": marketplace_id},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    urls = {u["url"] for u in body["urls"]}
    assert urls == {"https://example.com/a", "https://example.com/b"}


async def test_create_blank_name_400(user_client):
    resp = await user_client.post("/api/products", json={"name": "   ", "urls": []})
    assert resp.status_code == 400


async def test_get_own_product(user_client):
    create = await user_client.post("/api/products", json={"name": "Mine", "urls": []})
    pid = create.json()["product_id"]
    resp = await user_client.get(f"/api/products/{pid}")
    assert resp.status_code == 200
    assert resp.json()["product_id"] == pid


async def test_get_other_users_product_404(user_client, other_user_client):
    create = await user_client.post(
        "/api/products", json={"name": "A's product", "urls": []}
    )
    pid = create.json()["product_id"]
    resp = await other_user_client.get(f"/api/products/{pid}")
    assert resp.status_code == 404


async def test_update_product_name(user_client):
    create = await user_client.post("/api/products", json={"name": "Old name", "urls": []})
    pid = create.json()["product_id"]
    resp = await user_client.patch(f"/api/products/{pid}", json={"name": "New name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New name"


async def test_delete_own_product(user_client):
    create = await user_client.post("/api/products", json={"name": "To delete", "urls": []})
    pid = create.json()["product_id"]
    resp = await user_client.delete(f"/api/products/{pid}")
    assert resp.status_code == 204
    gone = await user_client.get(f"/api/products/{pid}")
    assert gone.status_code == 404


async def test_delete_other_users_product_404(user_client, other_user_client):
    create = await user_client.post("/api/products", json={"name": "Mine", "urls": []})
    pid = create.json()["product_id"]
    resp = await other_user_client.delete(f"/api/products/{pid}")
    assert resp.status_code == 404
    still = await user_client.get(f"/api/products/{pid}")
    assert still.status_code == 200


async def test_list_returns_only_own_products(user_client, other_user_client):
    await user_client.post("/api/products", json={"name": "A1", "urls": []})
    await user_client.post("/api/products", json={"name": "A2", "urls": []})
    await other_user_client.post("/api/products", json={"name": "B1", "urls": []})

    a_list = await user_client.get("/api/products")
    b_list = await other_user_client.get("/api/products")

    assert {p["name"] for p in a_list.json()} == {"A1", "A2"}
    assert {p["name"] for p in b_list.json()} == {"B1"}
