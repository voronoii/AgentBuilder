from __future__ import annotations

from typing import Protocol

from langchain_core.language_models import BaseChatModel


class ChatModelFactory(Protocol):
    async def create(self, model_name: str, **kwargs) -> BaseChatModel: ...
