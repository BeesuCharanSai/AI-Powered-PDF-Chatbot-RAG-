"""This "graph" simply exposes an endpoint for a user to upload docs to be indexed."""

from __future__ import annotations

import json
import os
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.ingestion_graph.configuration import (
    IndexConfiguration,
    ensure_index_configuration,
)
from src.ingestion_graph.state import IndexState
from src.shared.retrieval import make_retriever
from src.shared.state import reduce_docs


async def ingest_docs(state: IndexState, config: Optional[RunnableConfig] = None) -> dict:
    """Ingest documents into the configured vector store.

    If no documents are provided in state, falls back to a sample document
    file when `use_sample_docs` is enabled in the configuration.
    """
    if not config:
        raise ValueError("Configuration required to run ingest_docs.")

    configuration = ensure_index_configuration(config)
    docs = state.get("docs")

    if not docs:
        if configuration.use_sample_docs:
            docs_path = configuration.docs_file
            if not os.path.isabs(docs_path):
                # Resolve relative to the backend package root (this file's
                # grandparent directory), matching the TS implementation's
                # use of a path relative to the process working directory.
                docs_path = os.path.join(os.getcwd(), docs_path.lstrip("./"))
            with open(docs_path, "r", encoding="utf-8") as f:
                serialized_docs = json.load(f)
            docs = reduce_docs([], serialized_docs)
        else:
            raise ValueError("No sample documents to index.")
    else:
        docs = reduce_docs([], docs)

    retriever = make_retriever(config)
    await retriever.aadd_documents(docs)

    return {"docs": "delete"}


# Define the graph.
# Note: we intentionally use `config_schema` (not the newer `context_schema`)
# because the LangGraph Platform API / SDK (used by the Next.js frontend)
# configures runs via `config.configurable`, which `config_schema` documents.
builder = StateGraph(IndexState, config_schema=IndexConfiguration)
builder.add_node("ingestDocs", ingest_docs)
builder.add_edge(START, "ingestDocs")
builder.add_edge("ingestDocs", END)

# Compile into a graph object that you can invoke and deploy.
graph = builder.compile()
graph.name = "IngestionGraph"
