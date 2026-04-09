from __future__ import annotations
import asyncio
import logging
from langchain_huggingface import HuggingFaceEmbeddings

_log = logging.getLogger(__name__)

def _detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"

class LocalHfProvider:
    def __init__(self, model_path: str, device: str | None = None) -> None:
        self._device = device or _detect_device()
        _log.info("loading HF embedding model from %s on %s", model_path, self._device)
        self._model = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs={"device": self._device},
            encode_kwargs={"normalize_embeddings": True},
        )
        probe = self._model.embed_query("__probe__")
        self.dimension: int = len(probe)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._model.embed_documents, texts)
