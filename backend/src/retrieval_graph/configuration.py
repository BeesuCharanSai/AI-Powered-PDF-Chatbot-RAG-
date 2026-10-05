"""Configuration for the retrieval graph."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Optional

from langchain_core.runnables import RunnableConfig, ensure_config

from src.shared.configuration import BaseConfiguration


@dataclass(kw_only=True)
class AgentConfiguration(BaseConfiguration):
    """Configuration for the retrieval agent."""

    # The language model used for processing and refining queries.
    # Should be in the form: provider/model-name.
    query_model: str = field(default="groq/llama-3.3-70b-versatile")

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "AgentConfiguration":
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})


def ensure_agent_configuration(
    config: Optional[RunnableConfig] = None,
) -> AgentConfiguration:
    """Create an AgentConfiguration instance from a RunnableConfig object."""
    return AgentConfiguration.from_runnable_config(config)
