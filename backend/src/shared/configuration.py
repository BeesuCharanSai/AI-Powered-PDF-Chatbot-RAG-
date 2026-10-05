"""Define the base configurable parameters shared by both graphs."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Literal, Optional

from langchain_core.runnables import RunnableConfig, ensure_config


@dataclass(kw_only=True)
class BaseConfiguration:
    """Configuration class for indexing and retrieval operations.

    This class defines the parameters needed for configuring the indexing and
    retrieval processes, including the vector store provider and search
    parameters.
    """

    # The vector store provider to use for retrieval.
    # Options are "supabase", but you can add more providers here and
    # create their own retriever functions.
    retriever_provider: Literal["supabase"] = field(default="supabase")

    # Additional keyword arguments to pass to the search function of the
    # retriever for filtering.
    filter_kwargs: dict[str, Any] = field(default_factory=dict)

    # The number of documents to retrieve.
    k: int = field(default=5)

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "BaseConfiguration":
        """Create a BaseConfiguration instance from a RunnableConfig object."""
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})


def ensure_base_configuration(config: Optional[RunnableConfig] = None) -> BaseConfiguration:
    """Create a BaseConfiguration instance from a RunnableConfig object.

    Mirrors `ensureBaseConfiguration` from the TypeScript implementation.
    """
    return BaseConfiguration.from_runnable_config(config)
