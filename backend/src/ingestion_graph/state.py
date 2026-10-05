"""State definition for the ingestion graph."""

from __future__ import annotations

from typing import Annotated

from langchain_core.documents import Document
from typing_extensions import TypedDict

from src.shared.state import reduce_docs


class IndexState(TypedDict):
    """Represents the state for document indexing/ingestion.

    Attributes:
        docs: A list of documents that the agent can index. New values are
            merged into the existing list via `reduce_docs`, and the special
            value "delete" clears the list (used once ingestion completes).
    """

    docs: Annotated[list[Document], reduce_docs]
