"""Shared state utilities: document reducer used by both graphs."""

from __future__ import annotations

import uuid
from typing import Any, Literal, Sequence, Union

from langchain_core.documents import Document

# The type of a "new docs" payload that can be applied on top of existing docs.
DocsInput = Union[
    Sequence[Document],
    Sequence[dict[str, Any]],
    Sequence[str],
    str,
    Literal["delete"],
]


def reduce_docs(
    existing: Sequence[Document] | None,
    new: DocsInput | None,
) -> list[Document]:
    """Reduce the document array based on the provided new documents or actions.

    This mirrors `reduceDocs` from the TypeScript implementation and is used
    as the reducer for the `docs` / `documents` state fields in both graphs.

    Args:
        existing: The existing list of documents in state.
        new: New documents to merge in, a single string to add as a new
            document, or the literal string "delete" to clear all documents.

    Returns:
        The updated list of documents.
    """
    if new == "delete":
        return []

    existing_list: list[Document] = list(existing) if existing else []
    existing_ids = {doc.metadata.get("uuid") for doc in existing_list}

    if isinstance(new, str):
        doc_id = str(uuid.uuid4())
        return existing_list + [Document(page_content=new, metadata={"uuid": doc_id})]

    new_list: list[Document] = []
    if isinstance(new, (list, tuple)):
        for item in new:
            if isinstance(item, str):
                item_id = str(uuid.uuid4())
                new_list.append(Document(page_content=item, metadata={"uuid": item_id}))
                existing_ids.add(item_id)
            elif isinstance(item, Document):
                metadata = dict(item.metadata or {})
                item_id = metadata.get("uuid") or str(uuid.uuid4())
                if item_id not in existing_ids:
                    new_list.append(
                        Document(
                            page_content=item.page_content,
                            metadata={**metadata, "uuid": item_id},
                        )
                    )
                    existing_ids.add(item_id)
            elif isinstance(item, dict):
                if "page_content" in item or "pageContent" in item:
                    metadata = dict(item.get("metadata") or {})
                    item_id = metadata.get("uuid") or str(uuid.uuid4())
                    if item_id not in existing_ids:
                        new_list.append(
                            Document(
                                page_content=item.get("page_content")
                                or item.get("pageContent")
                                or "",
                                metadata={**metadata, "uuid": item_id},
                            )
                        )
                        existing_ids.add(item_id)
                else:
                    # Generic object/dict, treat it as metadata.
                    item_id = item.get("uuid") or str(uuid.uuid4())
                    if item_id not in existing_ids:
                        new_list.append(
                            Document(page_content="", metadata={**item, "uuid": item_id})
                        )
                        existing_ids.add(item_id)

    return existing_list + new_list
