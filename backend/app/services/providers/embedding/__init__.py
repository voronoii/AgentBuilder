from __future__ import annotations
from collections.abc import Callable
from typing import Any

from app.core.errors import AppError, ErrorCode
from app.services.providers.embedding.base import EmbeddingProvider

_Factory = Callable[..., EmbeddingProvider]
_REGISTRY: dict[str, _Factory] = {}

def register_embedding_provider(name: str, factory: _Factory) -> None:
    _REGISTRY[name] = factory

def get_embedding_provider(name: str, **kwargs: Any) -> EmbeddingProvider:
    try:
        factory = _REGISTRY[name]
    except KeyError as exc:
        raise AppError(
            status_code=400,
            code=ErrorCode.KNOWLEDGE_INVALID_INPUT,
            detail=f"unknown embedding provider: {name}",
        ) from exc
    return factory(**kwargs)

def build_default_provider(settings: Any) -> EmbeddingProvider:
    provider_name = settings.default_embedding_provider
    if provider_name == "local_hf":
        return get_embedding_provider("local_hf", model_path=settings.default_embedding_model_path)
    return get_embedding_provider(provider_name)

def _register_defaults() -> None:
    from app.services.providers.embedding.fastembed_provider import FastembedProvider
    register_embedding_provider("fastembed", lambda **kw: FastembedProvider(**kw))

    from app.services.providers.embedding.local_hf import LocalHfProvider

    def _local_hf_factory(**kw: Any) -> EmbeddingProvider:
        try:
            return LocalHfProvider(**kw)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("local_hf load failed (%s); falling back to fastembed", exc)
            return FastembedProvider()

    register_embedding_provider("local_hf", _local_hf_factory)

_register_defaults()

__all__ = ["EmbeddingProvider", "get_embedding_provider", "register_embedding_provider", "build_default_provider"]
