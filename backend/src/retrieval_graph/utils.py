"""Utility functions for the retrieval graph."""

from __future__ import annotations

from typing import Optional, Sequence

from langchain_core.documents import Document


def format_doc(doc: Document) -> str:
    """Format a single document as an XML-ish snippet with its metadata."""
    metadata = doc.metadata or {}
    meta = "".join(f" {k}={v}" for k, v in metadata.items())
    meta_str = f" {meta}" if meta else ""
    return f"<document{meta_str}>\n{doc.page_content}\n</document>"


def format_docs(docs: Optional[Sequence[Document]]) -> str:
    """Format a list of documents as XML."""
    if not docs:
        return "<documents></documents>"
    formatted = "\n".join(format_doc(doc) for doc in docs)
    return f"<documents>\n{formatted}\n</documents>"
