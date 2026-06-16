from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass
class AIReport:
    used: bool
    provider: str
    model: str | None
    report: dict[str, Any] | None
    error: str | None = None
    raw_text: str | None = None


REPORT_INSTRUCTIONS = """
Ты эксперт по анализу интерактивных многостраничных изданий.
Работай только с фактами из входного JSON: page, features, rubric.
Не выдумывай просмотренные экраны, поведение пользователей или метрики, которых нет во входных данных.

Сформируй отчет на русском языке по методике:
1. краткий вывод;
2. достоинства;
3. недостатки;
4. рекомендации по улучшению;
5. оценка риска когнитивной нагрузки;
6. что нужно проверить вручную.

Верни только валидный JSON-объект с ключами:
summary, advantages, problems, recommendations, cognitive_load_risk, manual_checks.
Значения advantages, problems, recommendations, manual_checks должны быть массивами строк.
"""


def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": payload["page"],
        "features": {
            key: value
            for key, value in payload["features"].items()
            if key
            in {
                "title",
                "description",
                "language",
                "word_count",
                "estimated_reading_time_min",
                "headings",
                "links_count",
                "anchors_count",
                "buttons_count",
                "images_count",
                "images_without_alt",
                "videos_count",
                "videos_autoplay_count",
                "audios_count",
                "audios_autoplay_count",
                "iframes_count",
                "scripts_count",
                "nav_count",
                "has_viewport_meta",
                "css_media_queries_count",
                "aria_attributes_count",
                "unlabeled_buttons_count",
                "unlabeled_links_count",
                "interactive_elements_count",
                "onclick_handlers_count",
                "noscript_present",
                "evidence",
            }
        },
        "rubric": payload["rubric"],
    }


def _parse_json_report(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.removeprefix("```json").removeprefix("```").strip()
        clean = clean.removesuffix("```").strip()
    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError("AI response must be a JSON object.")
    return parsed


def _extract_openai_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"])

    parts: list[str] = []
    for item in response.get("output", []) or []:
        for content in item.get("content", []) or []:
            if isinstance(content, dict):
                if content.get("text"):
                    parts.append(str(content["text"]))
                elif content.get("value"):
                    parts.append(str(content["value"]))
    return "\n".join(parts)


def _extract_gemini_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for candidate in response.get("candidates", []) or []:
        content = candidate.get("content", {})
        for part in content.get("parts", []) or []:
            if isinstance(part, dict) and part.get("text"):
                parts.append(str(part["text"]))
    return "\n".join(parts)


def _post_json(url: str, body: dict[str, Any], headers: dict[str, str], timeout_seconds: int) -> str:
    request = Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def _http_error_message(provider: str, exc: HTTPError) -> str:
    detail = exc.read().decode("utf-8", errors="replace")
    return f"{provider} HTTP {exc.code}: {detail}"


def _generate_openai(
    payload: dict[str, Any],
    *,
    api_key: str | None,
    model: str,
    timeout_seconds: int,
) -> AIReport:
    provider = "openai"
    if not api_key:
        return AIReport(used=False, provider=provider, model=model, report=None, error="OPENAI_API_KEY is not configured.")

    body = {
        "model": model,
        "instructions": REPORT_INSTRUCTIONS.strip(),
        "input": json.dumps(payload, ensure_ascii=False),
        "max_output_tokens": 1800,
    }
    try:
        raw = _post_json(
            "https://api.openai.com/v1/responses",
            body,
            {"Authorization": f"Bearer {api_key}"},
            timeout_seconds,
        )
        text = _extract_openai_text(json.loads(raw)).strip()
        return AIReport(used=True, provider=provider, model=model, report=_parse_json_report(text), raw_text=text)
    except HTTPError as exc:
        return AIReport(used=False, provider=provider, model=model, report=None, error=_http_error_message("OpenAI", exc))
    except URLError as exc:
        return AIReport(used=False, provider=provider, model=model, report=None, error=f"OpenAI network error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        return AIReport(used=False, provider=provider, model=model, report=None, error=str(exc))


def _generate_gemini(
    payload: dict[str, Any],
    *,
    api_key: str | None,
    model: str,
    timeout_seconds: int,
) -> AIReport:
    provider = "gemini"
    if not api_key:
        return AIReport(used=False, provider=provider, model=model, report=None, error="GEMINI_API_KEY is not configured.")

    prompt = f"{REPORT_INSTRUCTIONS.strip()}\n\nВходные данные JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    query = urlencode({"key": api_key})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='')}:generateContent?{query}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1800,
            "responseMimeType": "application/json",
        },
    }

    try:
        raw = _post_json(url, body, {}, timeout_seconds)
        text = _extract_gemini_text(json.loads(raw)).strip()
        return AIReport(used=True, provider=provider, model=model, report=_parse_json_report(text), raw_text=text)
    except HTTPError as exc:
        return AIReport(used=False, provider=provider, model=model, report=None, error=_http_error_message("Gemini", exc))
    except URLError as exc:
        return AIReport(used=False, provider=provider, model=model, report=None, error=f"Gemini network error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        return AIReport(used=False, provider=provider, model=model, report=None, error=str(exc))


def _generate_ollama(
    payload: dict[str, Any],
    *,
    base_url: str,
    model: str,
    timeout_seconds: int,
) -> AIReport:
    provider = "ollama"
    prompt = f"{REPORT_INSTRUCTIONS.strip()}\n\nВходные данные JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    url = f"{base_url.rstrip('/')}/api/generate"
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
    }

    try:
        raw = _post_json(url, body, {}, timeout_seconds)
        data = json.loads(raw)
        text = str(data.get("response", "")).strip()
        return AIReport(used=True, provider=provider, model=model, report=_parse_json_report(text), raw_text=text)
    except HTTPError as exc:
        return AIReport(used=False, provider=provider, model=model, report=None, error=_http_error_message("Ollama", exc))
    except URLError as exc:
        return AIReport(used=False, provider=provider, model=model, report=None, error=f"Ollama network error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        return AIReport(used=False, provider=provider, model=model, report=None, error=str(exc))


def generate_ai_report(
    payload: dict[str, Any],
    *,
    provider: str,
    enabled: bool,
    openai_api_key: str | None,
    openai_model: str,
    gemini_api_key: str | None,
    gemini_model: str,
    ollama_base_url: str,
    ollama_model: str,
    timeout_seconds: int,
) -> AIReport:
    normalized_provider = provider.strip().lower()
    model_by_provider = {
        "openai": openai_model,
        "gemini": gemini_model,
        "ollama": ollama_model,
        "none": None,
    }
    selected_model = model_by_provider.get(normalized_provider)

    if not enabled:
        return AIReport(used=False, provider=normalized_provider, model=selected_model, report=None, error="AI is disabled.")
    if normalized_provider == "none":
        return AIReport(used=False, provider="none", model=None, report=None, error="AI provider is disabled.")
    if normalized_provider not in model_by_provider:
        return AIReport(
            used=False,
            provider=normalized_provider,
            model=None,
            report=None,
            error=f"Unsupported AI_PROVIDER '{provider}'. Use one of: none, openai, gemini, ollama.",
        )

    compact_payload = _compact_payload(payload)
    if normalized_provider == "openai":
        return _generate_openai(
            compact_payload,
            api_key=openai_api_key,
            model=openai_model,
            timeout_seconds=timeout_seconds,
        )
    if normalized_provider == "gemini":
        return _generate_gemini(
            compact_payload,
            api_key=gemini_api_key,
            model=gemini_model,
            timeout_seconds=timeout_seconds,
        )
    return _generate_ollama(
        compact_payload,
        base_url=ollama_base_url,
        model=ollama_model,
        timeout_seconds=timeout_seconds,
    )
