"""Provider-neutral chat model construction via LangChain `init_chat_model`.

Switch providers with env/config only, e.g. google_genai (free AI Studio key), openai,
anthropic, or any OpenAI-compatible endpoint (provider=openai + base_url).
"""

from __future__ import annotations

from typing import Any


def build_chat_model(
    *,
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.0,
) -> Any:
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {"temperature": temperature}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return init_chat_model(model, model_provider=provider, **kwargs)
