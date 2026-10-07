from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from applied_knowledge.domain.models import SourceRecord


class SourceAdapter(Protocol):
    """Boundary between an external source and the generic ingestion core.

    Crucially, adapters emit SourceRecord only. They do not create knowledge.
    """

    name: str
    version: str

    def fingerprint(self) -> str | None: ...

    def records(self) -> Iterable[SourceRecord]: ...
