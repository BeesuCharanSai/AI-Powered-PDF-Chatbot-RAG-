"""Quick demo script that talks to a locally running LangGraph server.

Environment variables needed:
  LANGGRAPH_API_URL: The URL where your LangGraph server is running
    - For local development: http://localhost:2024
    - For LangSmith cloud: https://api.smith.langchain.com

Run the dev server first with:
    langgraph dev

Then in another terminal:
    python demo.py
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()

ASSISTANT_ID = "retrieval_graph"


async def run_demo() -> None:
    client = get_client(url=os.environ.get("LANGGRAPH_API_URL", "http://localhost:2024"))

    print("Creating new thread...")
    thread = await client.threads.create(metadata={"demo": "retrieval-graph"})
    print("Thread created with ID:", thread["thread_id"])

    question = "What is this document about?"

    print("\n=== Streaming Example ===")
    print("Question:", question)

    print("\nStarting stream...")
    stream = client.runs.stream(
        thread["thread_id"],
        ASSISTANT_ID,
        input={"query": question},
        stream_mode=["values", "messages", "updates"],
    )

    print("\nWaiting for stream chunks...")
    async for chunk in stream:
        print("\nReceived chunk:")
        if chunk.event == "updates":
            print("Update data:", chunk.data)

    print("\nStream completed.")


if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except Exception as exc:  # noqa: BLE001
        print("Fatal error:", exc)
        raise
