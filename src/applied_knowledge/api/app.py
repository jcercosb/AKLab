from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query, Response, status

from applied_knowledge.knowledge import (
    KnowledgeNotFoundError,
    KnowledgeNotManualError,
    ManualKnowledgeService,
)
from applied_knowledge.storage.database import Database
from applied_knowledge.storage.repository import KnowledgeRepository
from applied_knowledge.search import SearchService, SqliteFtsIndex

from .schemas import (
    KnowledgeCreate,
    KnowledgePatch,
    KnowledgeRevisionView,
    KnowledgeSpaceCreate,
    KnowledgeSpaceView,
    KnowledgeView,
    SearchHitView,
)


def create_app(database_url: str | None = None) -> FastAPI:
    resolved_url = database_url or os.getenv("AKLAB_DATABASE_URL", "sqlite:///knowledge.db")
    database = Database(resolved_url)
    database.create_schema()
    with database.session() as session:
        SqliteFtsIndex(session).rebuild()

    app = FastAPI(
        title="Applied Knowledge Lab",
        version="0.2.0",
        description="Generic knowledge API with manual CRUD and classical search baselines.",
    )
    app.state.database = database

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/knowledge-spaces",
        response_model=KnowledgeSpaceView,
        status_code=status.HTTP_201_CREATED,
    )
    def create_space(payload: KnowledgeSpaceCreate) -> KnowledgeSpaceView:
        with database.session() as session:
            repo = KnowledgeRepository(session)
            row = repo.ensure_space(
                id=payload.id,
                name=payload.name,
                description=payload.description,
                metadata=payload.metadata,
            )
            return KnowledgeSpaceView.from_row(row)

    @app.get("/knowledge-spaces", response_model=list[KnowledgeSpaceView])
    def list_spaces() -> list[KnowledgeSpaceView]:
        with database.session() as session:
            repo = KnowledgeRepository(session)
            return [KnowledgeSpaceView.from_row(row) for row in repo.list_spaces()]

    @app.post(
        "/knowledge-spaces/{knowledge_space_id}/knowledge",
        response_model=KnowledgeView,
        status_code=status.HTTP_201_CREATED,
    )
    def create_knowledge(
        knowledge_space_id: str,
        payload: KnowledgeCreate,
    ) -> KnowledgeView:
        try:
            with database.session() as session:
                service = ManualKnowledgeService(
                    KnowledgeRepository(session),
                    search_index=SqliteFtsIndex(session),
                )
                row = service.create(
                    knowledge_space_id=knowledge_space_id,
                    item=payload.to_domain(),
                )
                return KnowledgeView.from_row(row)
        except KnowledgeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/knowledge-spaces/{knowledge_space_id}/knowledge",
        response_model=list[KnowledgeView],
    )
    def list_knowledge(
        knowledge_space_id: str,
        kind: str | None = None,
        include_archived: bool = Query(default=False),
    ) -> list[KnowledgeView]:
        try:
            with database.session() as session:
                service = ManualKnowledgeService(
                    KnowledgeRepository(session),
                    search_index=SqliteFtsIndex(session),
                )
                rows = service.list(
                    knowledge_space_id=knowledge_space_id,
                    kind=kind,
                    status=None if include_archived else "active",
                )
                return [KnowledgeView.from_row(row) for row in rows]
        except KnowledgeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/knowledge-spaces/{knowledge_space_id}/knowledge/{knowledge_item_id}",
        response_model=KnowledgeView,
    )
    def get_knowledge(
        knowledge_space_id: str,
        knowledge_item_id: str,
    ) -> KnowledgeView:
        try:
            with database.session() as session:
                service = ManualKnowledgeService(
                    KnowledgeRepository(session),
                    search_index=SqliteFtsIndex(session),
                )
                return KnowledgeView.from_row(
                    service.get(
                        knowledge_space_id=knowledge_space_id,
                        knowledge_item_id=knowledge_item_id,
                    )
                )
        except KnowledgeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.patch(
        "/knowledge-spaces/{knowledge_space_id}/knowledge/{knowledge_item_id}",
        response_model=KnowledgeView,
    )
    def update_knowledge(
        knowledge_space_id: str,
        knowledge_item_id: str,
        payload: KnowledgePatch,
    ) -> KnowledgeView:
        try:
            with database.session() as session:
                service = ManualKnowledgeService(
                    KnowledgeRepository(session),
                    search_index=SqliteFtsIndex(session),
                )
                row = service.update(
                    knowledge_space_id=knowledge_space_id,
                    knowledge_item_id=knowledge_item_id,
                    changes=payload.to_changes(),
                )
                return KnowledgeView.from_row(row)
        except KnowledgeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except KnowledgeNotManualError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get(
        "/knowledge-spaces/{knowledge_space_id}/knowledge/{knowledge_item_id}/revisions",
        response_model=list[KnowledgeRevisionView],
    )
    def list_revisions(
        knowledge_space_id: str,
        knowledge_item_id: str,
    ) -> list[KnowledgeRevisionView]:
        try:
            with database.session() as session:
                repo = KnowledgeRepository(session)
                service = ManualKnowledgeService(repo)
                service.get(
                    knowledge_space_id=knowledge_space_id,
                    knowledge_item_id=knowledge_item_id,
                )
                return [
                    KnowledgeRevisionView(
                        revision=row.revision,
                        snapshot=row.snapshot,
                        author_type=row.author_type,
                        created_at=row.created_at.isoformat(),
                    )
                    for row in repo.list_knowledge_revisions(
                        knowledge_item_id=knowledge_item_id
                    )
                ]
        except KnowledgeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete(
        "/knowledge-spaces/{knowledge_space_id}/knowledge/{knowledge_item_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def archive_knowledge(
        knowledge_space_id: str,
        knowledge_item_id: str,
    ) -> Response:
        try:
            with database.session() as session:
                service = ManualKnowledgeService(
                    KnowledgeRepository(session),
                    search_index=SqliteFtsIndex(session),
                )
                service.archive(
                    knowledge_space_id=knowledge_space_id,
                    knowledge_item_id=knowledge_item_id,
                )
                return Response(status_code=status.HTTP_204_NO_CONTENT)
        except KnowledgeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except KnowledgeNotManualError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get(
        "/knowledge-spaces/{knowledge_space_id}/search",
        response_model=list[SearchHitView],
    )
    def search_knowledge(
        knowledge_space_id: str,
        q: str | None = None,
        mode: str = Query(default="fts", pattern="^(exact|fts)$"),
        kind: str | None = None,
        include_archived: bool = Query(default=False),
        attribute_name: str | None = None,
        attribute_value: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> list[SearchHitView]:
        if mode == "fts" and not q:
            raise HTTPException(status_code=400, detail="q is required for fts mode")
        if mode == "exact" and q is None and attribute_name is None and attribute_value is None and kind is None:
            raise HTTPException(
                status_code=400,
                detail="exact mode requires q or at least one filter",
            )
        try:
            with database.session() as session:
                service = SearchService(session)
                common = dict(
                    knowledge_space_id=knowledge_space_id,
                    kind=kind,
                    status=None if include_archived else "active",
                    attribute_name=attribute_name,
                    attribute_value=attribute_value,
                    limit=limit,
                )
                if mode == "exact":
                    hits = service.exact(query=q, **common)
                else:
                    hits = service.fts(query=q or "", **common)
                return [
                    SearchHitView(
                        knowledge_item_id=hit.knowledge_item_id,
                        origin_key=hit.origin_key,
                        kind=hit.kind,
                        title=hit.title,
                        status=hit.status,
                        score=hit.score,
                        match_type=hit.match_type,
                    )
                    for hit in hits
                ]
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/knowledge-spaces/{knowledge_space_id}/search-index/rebuild",
        status_code=status.HTTP_200_OK,
    )
    def rebuild_search_index(knowledge_space_id: str) -> dict[str, int]:
        with database.session() as session:
            repo = KnowledgeRepository(session)
            if repo.get_space(knowledge_space_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"KnowledgeSpace not found: {knowledge_space_id}",
                )
            count = SqliteFtsIndex(session).rebuild(knowledge_space_id=knowledge_space_id)
            return {"indexed": count}

    return app

