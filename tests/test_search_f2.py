from __future__ import annotations

from fastapi.testclient import TestClient

from applied_knowledge.api.app import create_app
from applied_knowledge.domain.models import KnowledgeAttributeData, KnowledgeItemData, KnowledgeSectionData
from applied_knowledge.knowledge import ManualKnowledgeService
from applied_knowledge.search import SearchService, SqliteFtsIndex
from applied_knowledge.storage.database import Database
from applied_knowledge.storage.repository import KnowledgeRepository


def _create_demo_items(session):
    repo = KnowledgeRepository(session)
    repo.ensure_space(id="demo", name="Demo")
    index = SqliteFtsIndex(session)
    service = ManualKnowledgeService(repo, search_index=index)
    timeout = service.create(
        knowledge_space_id="demo",
        item=KnowledgeItemData(
            kind="parameter",
            title="TIMEOUT_API",
            summary="Timeout for external API calls",
            content="Recommended value is 30 seconds.",
            sections=(
                KnowledgeSectionData(
                    kind="diagnostic",
                    content="Check this parameter when error E102 appears.",
                ),
            ),
            attributes=(
                KnowledgeAttributeData(name="recommended_value", value="30", value_type="integer"),
                KnowledgeAttributeData(name="related_error", value="E102"),
            ),
        ),
    )
    printer = service.create(
        knowledge_space_id="demo",
        item=KnowledgeItemData(
            kind="support_case",
            title="Printer configuration",
            content="Restart the program after changing printer settings.",
            attributes=(KnowledgeAttributeData(name="module", value="printing"),),
        ),
    )
    return service, timeout, printer


def test_exact_search_and_structured_filters() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()
    with db.session() as session:
        _create_demo_items(session)
        search = SearchService(session)

        hits = search.exact(knowledge_space_id="demo", query="TIMEOUT_API")
        assert [hit.title for hit in hits] == ["TIMEOUT_API"]
        assert hits[0].match_type == "exact"
        assert hits[0].score is None

        hits = search.exact(
            knowledge_space_id="demo",
            attribute_name="related_error",
            attribute_value="E102",
        )
        assert [hit.title for hit in hits] == ["TIMEOUT_API"]

        hits = search.exact(knowledge_space_id="demo", kind="support_case")
        assert [hit.title for hit in hits] == ["Printer configuration"]


def test_fts_searches_title_sections_and_attributes() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()
    with db.session() as session:
        _create_demo_items(session)
        search = SearchService(session)

        title_hits = search.fts(knowledge_space_id="demo", query="TIMEOUT_API")
        assert title_hits[0].title == "TIMEOUT_API"
        assert title_hits[0].score is not None

        section_hits = search.fts(knowledge_space_id="demo", query="E102")
        assert section_hits[0].title == "TIMEOUT_API"

        attribute_hits = search.fts(knowledge_space_id="demo", query="printing")
        assert attribute_hits[0].title == "Printer configuration"


def test_manual_update_refreshes_fts_and_archive_is_filtered() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()
    with db.session() as session:
        service, timeout, _ = _create_demo_items(session)
        search = SearchService(session)

        assert search.fts(knowledge_space_id="demo", query="latency") == []

        service.update(
            knowledge_space_id="demo",
            knowledge_item_id=timeout.id,
            changes={"content": "Latency limit for partner integrations."},
        )
        hits = search.fts(knowledge_space_id="demo", query="latency")
        assert [hit.knowledge_item_id for hit in hits] == [timeout.id]

        service.archive(knowledge_space_id="demo", knowledge_item_id=timeout.id)
        assert search.fts(knowledge_space_id="demo", query="latency") == []
        archived = search.fts(
            knowledge_space_id="demo",
            query="latency",
            status=None,
        )
        assert [hit.knowledge_item_id for hit in archived] == [timeout.id]


def test_rebuild_restores_derived_index() -> None:
    db = Database("sqlite+pysqlite:///:memory:")
    db.create_schema()
    with db.session() as session:
        repo = KnowledgeRepository(session)
        repo.ensure_space(id="demo", name="Demo")
        service = ManualKnowledgeService(repo)
        service.create(
            knowledge_space_id="demo",
            item=KnowledgeItemData(kind="concept", title="Hybrid retrieval", content="Lexical plus semantic retrieval."),
        )

        search = SearchService(session)
        assert search.fts(knowledge_space_id="demo", query="semantic") == []
        assert SqliteFtsIndex(session).rebuild(knowledge_space_id="demo") == 1
        assert search.fts(knowledge_space_id="demo", query="semantic")[0].title == "Hybrid retrieval"


def test_f2_search_api(tmp_path) -> None:
    app = create_app(f"sqlite:///{tmp_path / 'f2.sqlite'}")
    client = TestClient(app)

    assert client.post("/knowledge-spaces", json={"id": "demo", "name": "Demo"}).status_code == 201
    created = client.post(
        "/knowledge-spaces/demo/knowledge",
        json={
            "kind": "parameter",
            "title": "TIMEOUT_API",
            "content": "Maximum wait time for API requests.",
            "attributes": [{"name": "recommended_value", "value": "30", "value_type": "integer"}],
        },
    )
    assert created.status_code == 201

    response = client.get("/knowledge-spaces/demo/search", params={"q": "maximum wait", "mode": "fts"})
    assert response.status_code == 200
    assert response.json()[0]["title"] == "TIMEOUT_API"
    assert response.json()[0]["match_type"] == "fts"

    response = client.get(
        "/knowledge-spaces/demo/search",
        params={
            "mode": "exact",
            "attribute_name": "recommended_value",
            "attribute_value": "30",
        },
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "TIMEOUT_API"

    response = client.post("/knowledge-spaces/demo/search-index/rebuild")
    assert response.status_code == 200
    assert response.json() == {"indexed": 1}
