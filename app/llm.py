from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from dataclasses import dataclass
from typing import Any


@dataclass
class AIReport:
    used: bool
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


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    return "\n".join(parts)


def _extract_output_text_from_json(response: dict[str, Any]) -> str:
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


def _generate_with_http(payload: dict, *, api_key: str, model: str) -> AIReport:
    body = {
        "model": model,
        "instructions": REPORT_INSTRUCTIONS.strip(),
        "input": json.dumps(payload, ensure_ascii=False),
        "max_output_tokens": 1800,
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return AIReport(used=False, model=model, report=None, error=f"OpenAI HTTP {exc.code}: {detail}")
    except URLError as exc:
        return AIReport(used=False, model=model, report=None, error=f"OpenAI network error: {exc.reason}")

    try:
        data = json.loads(raw)
        text = _extract_output_text_from_json(data).strip()
        parsed = json.loads(text)
        return AIReport(used=True, model=model, report=parsed, raw_text=text)
    except Exception as exc:  # noqa: BLE001
        return AIReport(used=False, model=model, report=None, error=str(exc), raw_text=raw[:4000])


def generate_ai_report(
    payload: dict,
    *,
    api_key: str | None,
    model: str,
    enabled: bool,
) -> AIReport:
    if not enabled:
        return AIReport(used=False, model=model, report=None, error="AI is disabled.")
    if not api_key:
        return AIReport(used=False, model=model, report=None, error="OPENAI_API_KEY is not configured.")

    compact_payload = {
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

    try:
        from openai import OpenAI
    except ImportError:
        return _generate_with_http(compact_payload, api_key=api_key, model=model)

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=model,
            instructions=REPORT_INSTRUCTIONS.strip(),
            input=json.dumps(compact_payload, ensure_ascii=False),
            max_output_tokens=1800,
        )
        text = _extract_output_text(response).strip()
        parsed = json.loads(text)
        return AIReport(used=True, model=model, report=parsed, raw_text=text)
    except Exception as exc:  # noqa: BLE001 - API failures should not break deterministic report.
        return AIReport(used=False, model=model, report=None, error=str(exc))
