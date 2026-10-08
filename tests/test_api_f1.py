from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from applied_knowledge.api.app import create_app


def test_f1_manual_crud_api(tmp_path: Path) -> None:
    db_path = tmp_path / "knowledge.sqlite"
    app = create_app(f"sqlite:///{db_path}")
    client = TestClient(app)

    response = client.post(
        "/knowledge-spaces",
        json={
            "id": "demo",
            "name": "Demo product",
            "description": "Empty product created without SAT",
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] == "demo"

    response = client.post(
        "/knowledge-spaces/demo/knowledge",
        json={
            "kind": "parameter",
            "title": "TIMEOUT_API",
            "content": "Controls the maximum wait time.",
            "sections": [
                {
                    "kind": "procedure",
                    "content": "Check TIMEOUT_API when E102 appears.",
                    "position": 0,
                }
            ],
            "attributes": [
                {
                    "name": "recommended_value",
                    "value": "30",
                    "value_type": "integer",
                }
            ],
        },
    )
    assert response.status_code == 201
    created = response.json()
    item_id = created["id"]
    assert created["status"] == "active"
    assert created["confidence"] is None
    assert created["attributes"][0]["value"] == "30"

    response = client.get(f"/knowledge-spaces/demo/knowledge/{item_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "TIMEOUT_API"

    response = client.patch(
        f"/knowledge-spaces/demo/knowledge/{item_id}",
        json={
            "title": "TIMEOUT_API revised",
            "attributes": [
                {
                    "name": "recommended_value",
                    "value": "45",
                    "value_type": "integer",
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["title"] == "TIMEOUT_API revised"
    assert response.json()["attributes"][0]["value"] == "45"

    response = client.get("/knowledge-spaces/demo/knowledge")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/knowledge-spaces/demo/knowledge/{item_id}/revisions"
    )
    assert response.status_code == 200
    assert [row["revision"] for row in response.json()] == [1, 2]

    response = client.delete(f"/knowledge-spaces/demo/knowledge/{item_id}")
    assert response.status_code == 204

    response = client.get("/knowledge-spaces/demo/knowledge")
    assert response.status_code == 200
    assert response.json() == []

    response = client.get("/knowledge-spaces/demo/knowledge?include_archived=true")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "archived"

    response = client.get(
        f"/knowledge-spaces/demo/knowledge/{item_id}/revisions"
    )
    assert response.status_code == 200
    assert [row["revision"] for row in response.json()] == [1, 2, 3]
    assert response.json()[-1]["snapshot"]["status"] == "archived"
