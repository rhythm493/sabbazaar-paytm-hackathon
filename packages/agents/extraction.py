"""Bill extraction: LLM structured output, or a clearly labelled deterministic fixture fallback."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from agents.prompts import SYSTEM_PROMPT, USER_PROMPT
from contracts.bill import BillExtraction

log = logging.getLogger(__name__)


class ExtractionFailed(Exception):
    pass


@dataclass
class ExtractionResult:
    extraction: BillExtraction
    fallback_used: bool
    provider: str
    model: str


class Extractor(Protocol):
    def extract(self, content: bytes, media_type: str) -> ExtractionResult: ...


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def document_block(content: bytes, media_type: str) -> dict[str, Any]:
    b64 = base64.b64encode(content).decode()
    kind = "file" if media_type == "application/pdf" else "image"
    # LangChain v1 standard content block; provider packages translate it.
    return {"type": kind, "base64": b64, "mime_type": media_type}


class LLMExtractor:
    def __init__(self, model: Any, *, provider: str, model_name: str, max_attempts: int = 3):
        self._structured = model.with_structured_output(BillExtraction)
        self.provider, self.model_name, self.max_attempts = provider, model_name, max_attempts

    def extract(self, content: bytes, media_type: str) -> ExtractionResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=[{"type": "text", "text": USER_PROMPT}, document_block(content, media_type)]
            ),
        ]
        last: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                out = self._structured.invoke(messages)
                if isinstance(out, dict):
                    out = BillExtraction.model_validate(out)
                if not isinstance(out, BillExtraction):
                    raise ExtractionFailed("model returned no structured output")
                return ExtractionResult(out, False, self.provider, self.model_name)
            except (ValidationError, ExtractionFailed, ValueError) as exc:
                last = exc
                log.warning("bill extraction attempt %d failed: %s", attempt, type(exc).__name__)
            except Exception as exc:  # provider/network errors
                last = exc
                log.warning("bill extraction attempt %d error: %s", attempt, type(exc).__name__)
        raise ExtractionFailed(f"extraction failed after {self.max_attempts} attempts") from last


class FixtureExtractor:
    """Returns pre-recorded extractions for known bill files. Always marks fallback_used=True."""

    def __init__(self, by_hash: dict[str, BillExtraction]):
        self._by_hash = by_hash

    @classmethod
    def from_dir(cls, directory: Path) -> FixtureExtractor:
        by_hash: dict[str, BillExtraction] = {}
        for spec in directory.glob("*.extraction.json"):
            stem = spec.name.removesuffix(".extraction.json")
            extraction = BillExtraction.model_validate(json.loads(spec.read_text("utf-8")))
            for doc in directory.glob(f"{stem}.*"):
                if doc.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".pdf"):
                    by_hash[content_hash(doc.read_bytes())] = extraction
        return cls(by_hash)

    def extract(self, content: bytes, media_type: str) -> ExtractionResult:
        found = self._by_hash.get(content_hash(content))
        if found is None:
            raise ExtractionFailed(
                "model is disabled and no recorded extraction exists for this bill"
            )
        return ExtractionResult(found.model_copy(deep=True), True, "fixture", "fixture")
