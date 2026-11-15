"""Sarvam speech-to-text and command parsing. Never talks to connectors.

``transcribe_audio`` sends a short audio clip to the Sarvam REST endpoint and
returns the transcript. ``propose_inventory_commands`` parses an instruction
into structured ``CommandExtraction`` values using the provider-neutral chat
model (ADR 0007). The caller is responsible for resolving products, storing
proposed actions and running the approval gate.
"""

from __future__ import annotations

import os

import httpx

from sabbazaar_contracts.commands import CommandExtraction

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_MODEL = "saaras:v4"  # default; saaras:v3 accepted by the same endpoint

# Sarvam validates an exact, parameterless MIME type. Browsers hand us e.g.
# "audio/webm;codecs=opus" — strip the parameters and remap the common
# "audio/x-*" aliases to their accepted forms.
_CONTENT_TYPE_REMAP = {
    "audio/x-webm": "audio/webm",
    "audio/x-ogg": "audio/ogg",
    "audio/wave": "audio/wav",
    "audio/x-wav": "audio/wav",
}

_EXTENSION_FALLBACK = {
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".aac": "audio/aac",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
}


def normalize_audio_content_type(content_type: str | None, filename: str = "") -> str:
    """Return the base, Sarvam-accepted MIME type for the uploaded audio."""
    base = (content_type or "").split(";", 1)[0].strip().lower()
    base = _CONTENT_TYPE_REMAP.get(base, base)
    if base and base != "application/octet-stream":
        return base
    for ext, mime in _EXTENSION_FALLBACK.items():
        if filename.lower().endswith(ext):
            return mime
    return "application/octet-stream"  # accepted by Sarvam as-is

SYSTEM_PROMPT = """You convert a merchant's spoken inventory instruction (English or Hindi-English mix)
into structured inventory modification commands for their shop catalogue.

Operations:
- set_price: "set the price of X to 450" / "X ka price 450 kar do" -> op=set_price, price_inr=450
- set_stock: "stock of X to 40" / "X ka stock 40 kar do" -> op=set_stock, quantity=40 (absolute level)
- adjust_stock: "add 5 of X" / "X ka stock 5 kam karo" -> op=adjust_stock, delta=-5 (signed)

Rules:
- product_query is the shortest fragment that identifies the product (a name, SKU or ISBN).
- price_inr is required for set_price, quantity for set_stock, delta for adjust_stock. If any of
  these is missing or ambiguous, do NOT guess — put the offending fragment in `unparsed` instead.
- Never invent products or ids. Only extract what the instruction says.
- rationale: one short sentence per command, e.g. "Merchant asked to lower the price to 450."
- Anything that is not an inventory modification goes into `unparsed` verbatim.
"""

USER_PROMPT = "Instruction: {instruction}"


class SpeechError(Exception):
    """Speech configuration or upstream failure."""


class SpeechUnavailable(SpeechError):
    """Speech/LLM is not configured; the capability is unavailable."""


def speech_enabled() -> bool:
    return os.getenv("SPEECH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def transcribe_audio(
    audio: bytes,
    filename: str,
    content_type: str | None,
    *,
    api_key: str | None = None,
    mode: str | None = None,
    timeout: float = 30.0,
) -> tuple[str, str | None]:
    """Transcribe a short audio clip. Returns (transcript, language_code).

    Raises SpeechUnavailable when no key is configured and SpeechError on
    upstream failure. Never raises for a well-formed request with no speech.
    """
    key = (api_key if api_key is not None else os.getenv("SARVAM_API_KEY", "")).strip()
    if not key:
        raise SpeechUnavailable("SARVAM_API_KEY is not configured; speech input is disabled")
    media_type = normalize_audio_content_type(content_type, filename)
    try:
        resp = httpx.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": key},
            files={"file": (filename, audio, media_type)},
            data={
                "model": os.getenv("SARVAM_STT_MODEL", SARVAM_MODEL),
                "mode": mode or os.getenv("SARVAM_MODE", "translate"),
            },
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise SpeechError(f"Sarvam STT request failed: {exc}") from exc
    try:
        body = resp.json()
    except ValueError as exc:
        raise SpeechError(f"Sarvam STT returned non-JSON response (HTTP {resp.status_code})") from exc
    if resp.status_code >= 400:
        error = body.get("error", body) if isinstance(body, dict) else body
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise SpeechError(f"Sarvam STT failed (HTTP {resp.status_code}): {message}")
    transcript = str(body.get("transcript") or "").strip() if isinstance(body, dict) else ""
    language_code = body.get("language_code") if isinstance(body, dict) else None
    return transcript, language_code


def propose_inventory_commands(
    transcript: str,
    *,
    chat_model=None,
    max_attempts: int = 2,
):
    """Parse an instruction into structured commands.

    Uses the provider-neutral chat model (MODEL_PROVIDER/MODEL_NAME/MODEL_API_KEY/
    MODEL_BASE_URL). Raises SpeechUnavailable when no model is configured.
    """
    model_enabled = os.getenv("MODEL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    model_name = os.getenv("MODEL_NAME", "").strip()
    if chat_model is None:
        if not model_enabled or not model_name:
            raise SpeechUnavailable(
                "MODEL_NAME/MODEL_ENABLED are not configured; command parsing is disabled"
            )
        from sabbazaar_agents.models import build_chat_model

        chat_model = build_chat_model(
            provider=os.getenv("MODEL_PROVIDER", "openai"),
            model=model_name,
            api_key=os.getenv("MODEL_API_KEY", "").strip() or None,
            base_url=os.getenv("MODEL_BASE_URL", "").strip() or None,
            temperature=0.0,
        )

    from langchain_core.messages import HumanMessage, SystemMessage

    structured = chat_model.with_structured_output(CommandExtraction)
    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(USER_PROMPT.format(instruction=transcript))]
    last_exc: Exception | None = None
    for _ in range(max_attempts):
        try:
            out = structured.invoke(messages)
            return CommandExtraction.model_validate(out) if isinstance(out, dict) else out
        except Exception as exc:  # noqa: BLE001 — provider-specific parse failures
            last_exc = exc
    raise SpeechError(f"Could not parse the instruction: {last_exc}")
