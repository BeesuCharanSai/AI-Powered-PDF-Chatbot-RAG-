"""Configuration for the ingestion graph."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Optional

from langchain_core.runnables import RunnableConfig, ensure_config

from src.shared.configuration import BaseConfiguration

# This file references sample documents to index, based on the LangChain
# and LangGraph documentation pages bundled with this project.
DEFAULT_DOCS_FILE = "./src/sample_docs.json"


@dataclass(kw_only=True)
class IndexConfiguration(BaseConfiguration):
    """Configuration for the indexing/ingestion process."""

    # Path to a JSON file containing default documents to index.
    docs_file: str = field(default=DEFAULT_DOCS_FILE)
    use_sample_docs: bool = field(default=False)

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "IndexConfiguration":
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})


def ensure_index_configuration(
    config: Optional[RunnableConfig] = None,
) -> IndexConfiguration:
    """Create an IndexConfiguration instance from a RunnableConfig object."""
    return IndexConfiguration.from_runnable_config(config)
