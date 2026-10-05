"""State definition for the retrieval graph / agent."""

from __future__ import annotations

from typing import Annotated

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict

from src.shared.state import reduce_docs


class AgentState(TypedDict, total=False):
    """Represents the state of the retrieval graph / agent."""

    query: str
    route: str
    messages: Annotated[list[AnyMessage], add_messages]

    # Populated by the retriever. A list of documents the agent can
    # reference when generating a response.
    documents: Annotated[list[Document], reduce_docs]
