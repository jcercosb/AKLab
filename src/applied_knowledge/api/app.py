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

from .schemas import (
    KnowledgeCreate,
    KnowledgePatch,
    KnowledgeRevisionView,
    KnowledgeSpaceCreate,
    KnowledgeSpaceView,
    KnowledgeView,
)


def create_app(database_url: str | None = None) -> FastAPI:
    resolved_url = database_url or os.getenv("AKLAB_DATABASE_URL", "sqlite:///knowledge.db")
    database = Database(resolved_url)
    database.create_schema()

    app = FastAPI(
        title="Applied Knowledge Lab",
        version="0.1.0",
        description="Generic knowledge API. F1 starts with deterministic manual CRUD.",
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
                service = ManualKnowledgeService(KnowledgeRepository(session))
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
                service = ManualKnowledgeService(KnowledgeRepository(session))
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
                service = ManualKnowledgeService(KnowledgeRepository(session))
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
                service = ManualKnowledgeService(KnowledgeRepository(session))
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
                service = ManualKnowledgeService(KnowledgeRepository(session))
                service.archive(
                    knowledge_space_id=knowledge_space_id,
                    knowledge_item_id=knowledge_item_id,
                )
                return Response(status_code=status.HTTP_204_NO_CONTENT)
        except KnowledgeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except KnowledgeNotManualError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return app

