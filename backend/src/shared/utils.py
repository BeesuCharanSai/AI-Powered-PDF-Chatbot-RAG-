"""Shared utility functions used across the graphs."""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

SUPPORTED_PROVIDERS = {
    "openai",
    "anthropic",
    "azure_openai",
    "cohere",
    "google_vertexai",
    "google_genai",
    "ollama",
    "together",
    "fireworks",
    "mistralai",
    "groq",
    "bedrock",
    "cerebras",
    "deepseek",
    "xai",
}


def load_chat_model(fully_specified_name: str, temperature: float = 0.2) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Mirrors `loadChatModel` from the TypeScript implementation.

    Args:
        fully_specified_name: String in the format "provider/model" (e.g.
            "openai/gpt-4o" or "groq/llama-3.3-70b-versatile"), or just a
            model name if the provider can be inferred.
        temperature: Sampling temperature to use for the model.

    Returns:
        An initialized chat model instance.
    """
    if "/" in fully_specified_name:
        provider, model = fully_specified_name.split("/", 1)
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        return init_chat_model(model, model_provider=provider, temperature=temperature)

    if fully_specified_name not in SUPPORTED_PROVIDERS:
        # Not a "/"-delimited name — assume it's a bare model name and let
        # init_chat_model try to infer the provider.
        return init_chat_model(fully_specified_name, temperature=temperature)

    raise ValueError(f"Unsupported model: {fully_specified_name}")
