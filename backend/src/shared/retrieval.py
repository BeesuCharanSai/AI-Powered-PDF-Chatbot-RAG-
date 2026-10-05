"""Retriever factory functions used by both graphs."""

from __future__ import annotations

import os
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase.client import Client, create_client

from src.shared.configuration import BaseConfiguration, ensure_base_configuration


def make_supabase_retriever(configuration: BaseConfiguration) -> VectorStoreRetriever:
    """Create a retriever backed by a Supabase vector store."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables are not defined"
        )

    # Groq (used for the chat model) does not offer an embeddings endpoint,
    # so embeddings are generated via Google's free Gemini API instead.
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    supabase_client: Client = create_client(supabase_url, supabase_key)
    vector_store = SupabaseVectorStore(
        client=supabase_client,
        embedding=embeddings,
        table_name="documents",
        query_name="match_documents",
    )
    return vector_store.as_retriever(
        search_kwargs={"k": configuration.k, "filter": configuration.filter_kwargs}
    )


def make_retriever(config: Optional[RunnableConfig] = None) -> VectorStoreRetriever:
    """Create a retriever based on the configured retriever provider."""
    configuration = ensure_base_configuration(config)
    if configuration.retriever_provider == "supabase":
        return make_supabase_retriever(configuration)

    raise ValueError(f"Unsupported retriever provider: {configuration.retriever_provider}")
