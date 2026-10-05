"""Main retrieval agent graph: routes queries, retrieves docs, and answers."""

from __future__ import annotations

from typing import Literal, Optional

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from src.retrieval_graph.configuration import (
    AgentConfiguration,
    ensure_agent_configuration,
)
from src.retrieval_graph.prompts import RESPONSE_SYSTEM_PROMPT, ROUTER_SYSTEM_PROMPT
from src.retrieval_graph.state import AgentState
from src.retrieval_graph.utils import format_docs
from src.shared.retrieval import make_retriever
from src.shared.utils import load_chat_model


class RouteSchema(BaseModel):
    """Schema used to route an incoming query."""

    route: Literal["retrieve", "direct"]
    direct_answer: Optional[str] = None


async def check_query_type(state: AgentState, config: RunnableConfig) -> dict:
    """Decide whether the query needs document retrieval or can be answered directly."""
    configuration = ensure_agent_configuration(config)
    model = load_chat_model(configuration.query_model)

    formatted_prompt = await ROUTER_SYSTEM_PROMPT.ainvoke({"query": state["query"]})

    response = await model.with_structured_output(RouteSchema).ainvoke(
        formatted_prompt.to_string()
    )

    return {"route": response.route}


async def answer_query_directly(state: AgentState, config: RunnableConfig) -> dict:
    """Answer the user's query directly without retrieval."""
    configuration = ensure_agent_configuration(config)
    model = load_chat_model(configuration.query_model)
    user_human_message = HumanMessage(content=state["query"])

    response = await model.ainvoke([user_human_message])
    return {"messages": [user_human_message, response]}


def route_query(state: AgentState) -> Literal["retrieveDocuments", "directAnswer"]:
    """Conditional edge: send the query down the retrieval or direct-answer path."""
    route = state.get("route")
    if not route:
        raise ValueError("Route is not set")

    if route == "retrieve":
        return "retrieveDocuments"
    elif route == "direct":
        return "directAnswer"
    else:
        raise ValueError("Invalid route")


async def retrieve_documents(state: AgentState, config: RunnableConfig) -> dict:
    """Retrieve documents relevant to the query."""
    retriever = make_retriever(config)
    response = await retriever.ainvoke(state["query"])
    return {"documents": response}


async def generate_response(state: AgentState, config: RunnableConfig) -> dict:
    """Generate a response using the retrieved documents as context."""
    configuration = ensure_agent_configuration(config)
    context = format_docs(state.get("documents"))
    model = load_chat_model(configuration.query_model)

    formatted_prompt = await RESPONSE_SYSTEM_PROMPT.ainvoke(
        {"question": state["query"], "context": context}
    )

    user_human_message = HumanMessage(content=state["query"])

    # Create a human message with the formatted prompt that includes context.
    formatted_prompt_message = HumanMessage(content=formatted_prompt.to_string())

    message_history = [*state.get("messages", []), formatted_prompt_message]

    # Let the `add_messages` reducer handle the message history.
    response = await model.ainvoke(message_history)

    # Return both the current query and the AI response to be handled by
    # the state's message reducer.
    return {"messages": [user_human_message, response]}


builder = StateGraph(AgentState, config_schema=AgentConfiguration)
builder.add_node("retrieveDocuments", retrieve_documents)
builder.add_node("generateResponse", generate_response)
builder.add_node("checkQueryType", check_query_type)
builder.add_node("directAnswer", answer_query_directly)
builder.add_edge(START, "checkQueryType")
builder.add_conditional_edges(
    "checkQueryType", route_query, ["retrieveDocuments", "directAnswer"]
)
builder.add_edge("retrieveDocuments", "generateResponse")
builder.add_edge("generateResponse", END)
builder.add_edge("directAnswer", END)

graph = builder.compile()
graph.name = "RetrievalGraph"
