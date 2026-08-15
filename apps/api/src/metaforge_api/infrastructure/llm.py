"""Provider-agnostic LLM chat/tool-calling client. Two backends (Gemini
Flash, OpenAI) behind one interface so `ai_chat.py`'s tool-calling loop
never has to know which provider is configured — it speaks one canonical
message shape (OpenAI's, since it's the simpler of the two to round-trip)
and this module translates to/from Gemini's shape internally.

Both backends are called via plain httpx REST requests rather than either
vendor's SDK — one fewer heavyweight dependency, and the two APIs are
simple enough (a handful of JSON fields) that a thin adapter is less
surface area than pulling in `openai` and `google-generativeai` just to
wrap requests.post().

NOTE: written against each vendor's documented REST shape without a live
key to test against in this environment — Gemini's function-calling
multi-turn format in particular (which role a function *response* turn
uses) is the one detail most likely to need a small adjustment once
exercised against a real API key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

_TIMEOUT = 30.0


class LlmError(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    # Gemini-only: newer "thinking" models (e.g. gemini-3.x) attach a
    # thought_signature to each functionCall part and REJECT the next turn
    # with a 400 if that exact signature isn't echoed back alongside the
    # same function call when the conversation history is replayed — see
    # https://ai.google.dev/gemini-api/docs/thought-signatures. Opaque,
    # provider-specific, and meaningless to OpenAI, so it rides along on
    # the canonical ToolCall as an optional field rather than needing its
    # own parallel plumbing.
    signature: str | None = None


@dataclass
class LlmResult:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


# Canonical message shape used by callers (matches OpenAI's chat-completions
# message shape, since every provider adapter converts to/from this):
#   {"role": "system"|"user"|"assistant"|"tool", "content": str | None,
#    "tool_calls": [{"id": str, "name": str, "arguments": dict, "signature": str | None}] | None,
#    "tool_call_id": str | None}


async def chat(
    *,
    provider: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    force_tool: str | None = None,
    timeout: float = _TIMEOUT,
) -> LlmResult:
    """`force_tool`: name of a tool the model MUST call (no plain-text
    reply allowed) — used for the one-shot document-extraction call in
    doc_extraction.py, where a free-text response would defeat the whole
    point of a structured-output schema. Not used by the normal
    tool-calling loop in ai_chat.py, which passes None (model chooses)."""
    if provider == "gemini":
        return await _chat_gemini(api_key=api_key, model=model, messages=messages, tools=tools, force_tool=force_tool, timeout=timeout)
    if provider == "openai":
        return await _chat_openai(api_key=api_key, model=model, messages=messages, tools=tools, force_tool=force_tool, timeout=timeout)
    raise LlmError(f"unknown provider: {provider}")


async def list_models(*, provider: str, api_key: str) -> list[str]:
    """Model ids the given key can actually use, filtered to ones capable
    of chat/tool-calling (a raw provider model list also includes
    embedding, image, audio, and legacy-completion models the assistant
    has no use for) — lets the settings UI offer a dropdown instead of a
    free-text model name that's easy to typo."""
    if provider == "gemini":
        return await _list_models_gemini(api_key)
    if provider == "openai":
        return await _list_models_openai(api_key)
    raise LlmError(f"unknown provider: {provider}")


async def _list_models_gemini(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": api_key})
    if resp.status_code >= 400:
        raise LlmError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    models = []
    for m in data.get("models", []):
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        name = m.get("name", "")
        models.append(name.removeprefix("models/"))
    return sorted(models)


async def _list_models_openai(api_key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    if resp.status_code >= 400:
        raise LlmError(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    # OpenAI's /v1/models returns every model the account can see, including
    # embeddings/tts/whisper/image/moderation/legacy-completion ones that
    # can't do chat+tools — "gpt"/"o1"/"o3"/"o4" ids are the chat-capable
    # family; excluding the non-chat suffixes below keeps out the ones that
    # do match that prefix but still aren't usable here (whisper/tts/audio
    # variants are occasionally prefixed oddly across accounts).
    excluded_substrings = ("embedding", "tts", "whisper", "audio", "moderation", "image", "instruct", "davinci", "babbage", "dall-e")
    models = [
        m["id"]
        for m in data.get("data", [])
        if any(m["id"].startswith(p) for p in ("gpt-", "o1", "o3", "o4", "chatgpt"))
        and not any(x in m["id"] for x in excluded_substrings)
    ]
    return sorted(models)


async def _chat_openai(
    *, api_key: str, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
    force_tool: str | None = None, timeout: float = _TIMEOUT,
) -> LlmResult:
    payload_messages = []
    for m in messages:
        entry: dict[str, Any] = {"role": m["role"]}
        if m["role"] == "tool":
            # Tool-result content is a plain dict internally (see ai_chat.py) —
            # OpenAI's API requires message.content to be a string.
            entry["tool_call_id"] = m["tool_call_id"]
            entry["content"] = _json_dumps(m.get("content"))
        elif m["role"] == "assistant" and m.get("tool_calls"):
            entry["content"] = m.get("content")
            entry["tool_calls"] = [
                {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": _json_dumps(tc["arguments"])}}
                for tc in m["tool_calls"]
            ]
        elif m["role"] == "user" and m.get("images"):
            # Multimodal content: an array of parts instead of a plain
            # string, one image_url part per attached image (data: URI —
            # no separate upload step needed).
            parts: list[dict[str, Any]] = []
            if m.get("content"):
                parts.append({"type": "text", "text": m["content"]})
            for img in m["images"]:
                parts.append({"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['data']}"}})
            entry["content"] = parts
        elif m.get("content") is not None:
            entry["content"] = m["content"]
        payload_messages.append(entry)

    body: dict[str, Any] = {
        "model": model,
        "messages": payload_messages,
        "tools": [{"type": "function", "function": t} for t in tools],
        "tool_choice": "auto",
    }
    if force_tool:
        body["tool_choice"] = {"type": "function", "function": {"name": force_tool}}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
        )
    if resp.status_code >= 400:
        raise LlmError(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    choice = data["choices"][0]["message"]
    tool_calls = [
        ToolCall(id=tc["id"], name=tc["function"]["name"], arguments=_json_loads(tc["function"]["arguments"]))
        for tc in choice.get("tool_calls", []) or []
    ]
    return LlmResult(text=choice.get("content"), tool_calls=tool_calls)


async def _chat_gemini(
    *, api_key: str, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
    force_tool: str | None = None, timeout: float = _TIMEOUT,
) -> LlmResult:
    system_text = "\n\n".join(m["content"] for m in messages if m["role"] == "system" and m.get("content"))
    contents: list[dict[str, Any]] = []
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "user":
            parts: list[dict[str, Any]] = [{"text": m.get("content") or ""}]
            for img in m.get("images") or []:
                parts.append({"inline_data": {"mime_type": img["mime_type"], "data": img["data"]}})
            contents.append({"role": "user", "parts": parts})
        elif m["role"] == "assistant":
            parts: list[dict[str, Any]] = []
            if m.get("content"):
                parts.append({"text": m["content"]})
            for tc in m.get("tool_calls") or []:
                part: dict[str, Any] = {"functionCall": {"name": tc["name"], "args": tc["arguments"]}}
                if tc.get("signature"):
                    # Required on replay for "thinking" models (gemini-3.x) —
                    # see ToolCall.signature's docstring. Harmless to omit
                    # for models that never issued one in the first place.
                    part["thoughtSignature"] = tc["signature"]
                parts.append(part)
            contents.append({"role": "model", "parts": parts})
        elif m["role"] == "tool":
            contents.append(
                {"role": "function", "parts": [{"functionResponse": {"name": m["name"], "response": m.get("content") or {}}}]}
            )

    body: dict[str, Any] = {
        "contents": contents,
        "tools": [{"functionDeclarations": tools}],
    }
    if system_text:
        body["system_instruction"] = {"parts": [{"text": system_text}]}
    if force_tool:
        body["toolConfig"] = {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": [force_tool]}}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, params={"key": api_key}, json=body)
    if resp.status_code >= 400:
        raise LlmError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return LlmResult(text=None, tool_calls=[])
    parts = candidates[0].get("content", {}).get("parts", [])
    # `thought: true` parts are the model's internal reasoning (thinking
    # models only) — never meant to be shown to the user as if it were the
    # actual reply, so excluded even though we don't request them via
    # thinkingConfig.includeThoughts in the first place.
    text_parts = [p["text"] for p in parts if "text" in p and not p.get("thought")]
    tool_calls = [
        ToolCall(
            id=f"gemini-{i}",
            name=p["functionCall"]["name"],
            arguments=p["functionCall"].get("args") or {},
            signature=p.get("thoughtSignature"),
        )
        for i, p in enumerate(parts)
        if "functionCall" in p
    ]
    return LlmResult(text="\n".join(text_parts) if text_parts else None, tool_calls=tool_calls)


def _json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj)


def _json_loads(raw: str) -> dict[str, Any]:
    import json

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
