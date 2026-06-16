# API contract

Backend exposes a small JSON API for the frontend. The primary runtime is `python -m app.server`; it does not require FastAPI or other third-party packages.

## Base URL

Local development:

```text
http://127.0.0.1:8000
```

## CORS

The standard-library server sends permissive CORS headers:

```text
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

The frontend can call the API directly from a local dev server.

## Endpoints

### `GET /health`

Checks whether the backend is running.

Response `200`:

```json
{
  "status": "ok",
  "ai_enabled": true,
  "ai_provider": "none",
  "ai_model": null,
  "openai_model": "gpt-5.4-mini",
  "runtime": "stdlib-http"
}
```

Frontend use:

- show backend connection status;
- read currently configured AI provider and model;
- do not use this endpoint as an analysis result.

### `GET /api/rubric`

Returns the evaluation criteria shown in the UI.

Response `200`:

```json
{
  "criteria": [
    {
      "key": "visual_structure",
      "name": "Визуальная структура и композиция",
      "description": "Иерархия заголовков, сканируемость, смысловые блоки и композиционная ясность."
    }
  ]
}
```

Current criterion keys:

```text
visual_structure
navigation_control
interactivity_feedback
multimedia_cognition
accessibility
adaptability_technical
cognitive_transparency
```

### `POST /api/analyze`

Analyzes a publication URL.

Request headers:

```text
Content-Type: application/json
```

Request body:

```json
{
  "url": "https://example.com",
  "use_ai": true,
  "include_features": true
}
```

Fields:

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `url` | string | yes | - | URL of the publication. If scheme is omitted, backend tries `https://`. |
| `use_ai` | boolean | no | `true` | Whether to request an AI-generated report. |
| `include_features` | boolean | no | `true` | Whether to include low-level HTML features in the response. |

Response `200`:

```json
{
  "status": "ok",
  "page": {
    "requested_url": "https://example.com",
    "final_url": "https://example.com",
    "status_code": 200,
    "content_type": "text/html",
    "elapsed_ms": 421,
    "fetched_at": "2026-06-16T03:12:00.000000+00:00",
    "warnings": []
  },
  "features": {
    "title": "Example Domain",
    "description": "",
    "language": "en",
    "text_length": 142,
    "word_count": 25,
    "estimated_reading_time_min": 1,
    "headings": {
      "h1": ["Example Domain"],
      "h2": [],
      "h3": [],
      "h4": [],
      "h5": [],
      "h6": []
    },
    "links_count": 1,
    "anchors_count": 0,
    "buttons_count": 0,
    "inputs_count": 0,
    "forms_count": 0,
    "images_count": 0,
    "images_without_alt": 0,
    "videos_count": 0,
    "videos_autoplay_count": 0,
    "audios_count": 0,
    "audios_autoplay_count": 0,
    "iframes_count": 0,
    "scripts_count": 0,
    "nav_count": 0,
    "main_count": 0,
    "footer_count": 0,
    "has_viewport_meta": false,
    "css_media_queries_count": 0,
    "aria_attributes_count": 0,
    "unlabeled_buttons_count": 0,
    "unlabeled_links_count": 0,
    "interactive_elements_count": 1,
    "onclick_handlers_count": 0,
    "noscript_present": false,
    "total_tags_count": 12,
    "evidence": {
      "sample_h1": ["Example Domain"],
      "sample_h2": [],
      "media_total": 0,
      "autoplay_total": 0
    }
  },
  "rubric": {
    "overall_score": 2.86,
    "criteria": [
      {
        "key": "visual_structure",
        "name": "Визуальная структура и композиция",
        "score": 3,
        "findings": ["Страница имеет один главный заголовок, что помогает сформировать точку входа."],
        "recommendations": ["Разбить длинный материал на смысловые разделы с подзаголовками и якорями."],
        "evidence": {
          "h1_count": 1,
          "h2_count": 0,
          "word_count": 25
        }
      }
    ],
    "strengths": [],
    "weaknesses": [],
    "recommendations": []
  },
  "heuristic_report": {
    "summary": "Страница получила 2.86 из 5 по методической рубрике...",
    "advantages": [],
    "problems": [],
    "recommendations": [],
    "method_note": "Автоматическая оценка является первичным аудитом...",
    "source": {
      "requested_url": "https://example.com",
      "final_url": "https://example.com",
      "title": "Example Domain",
      "description": ""
    }
  },
  "ai": {
    "used": false,
    "provider": "none",
    "model": null,
    "report": null,
    "error": "AI provider is disabled."
  }
}
```

If `include_features=false`, the response still contains all high-level report fields, but:

```json
{
  "features": null
}
```

AI behavior:

- `ai.used=true` means the response contains an AI-generated `ai.report`.
- `ai.used=false` is not a request failure by itself. The frontend should still render `heuristic_report` and `rubric`.
- `ai.provider` is one of `none`, `openai`, `gemini`, `ollama`, or an unsupported configured value.
- `ai.error` explains why AI was skipped or failed.

AI report shape when available:

```json
{
  "summary": "Краткий экспертный вывод.",
  "advantages": ["..."],
  "problems": ["..."],
  "recommendations": ["..."],
  "cognitive_load_risk": "Низкий / средний / высокий риск...",
  "manual_checks": ["..."]
}
```

## Error responses

All errors are JSON:

```json
{
  "error": "Message"
}
```

Status codes:

| Status | When |
| --- | --- |
| `204` | `OPTIONS` preflight request. |
| `400` | Invalid JSON body, missing `url`, non-HTTP URL, localhost/private IP blocked. |
| `404` | Unknown route. |
| `502` | Backend could not fetch the target URL or target returned an HTTP/network error. |

Important URL rules:

- only `http://` and `https://` URLs are accepted;
- `localhost`, private IPs and local network addresses are blocked by default;
- this can be changed with `ALLOW_PRIVATE_URLS=true` for local demos;
- request body is limited to 64 KB;
- fetched response body is limited by `FETCH_MAX_BYTES`.

## Frontend fetch example

```ts
type AnalyzeRequest = {
  url: string;
  use_ai?: boolean;
  include_features?: boolean;
};

async function analyzePublication(payload: AnalyzeRequest) {
  const response = await fetch("http://127.0.0.1:8000/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error ?? "Analysis failed");
  }

  return data;
}
```

Recommended frontend rendering order:

1. Render `heuristic_report.summary`.
2. Render `rubric.overall_score` and `rubric.criteria`.
3. Render `ai.report` only when `ai.used === true`.
4. If `ai.used === false`, show a soft note only when useful; do not treat it as full analysis failure.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Enables AI report generation. |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Model used for AI report generation. |
| `AI_PROVIDER` | `none` unless `OPENAI_API_KEY` exists | AI provider: `none`, `openai`, `gemini`, `ollama`. |
| `AI_ENABLED` | `true` | Global switch for AI calls. |
| `GEMINI_API_KEY` | empty | Google Gemini API key. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model used when `AI_PROVIDER=gemini`. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama server URL. |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama model used when `AI_PROVIDER=ollama`. |
| `AI_REQUEST_TIMEOUT_SECONDS` | `60` | AI provider request timeout. |
| `ALLOW_PRIVATE_URLS` | `false` | Allows localhost/private IP analysis for demos. |
| `FETCH_TIMEOUT_SECONDS` | `15` | Target URL fetch timeout. |
| `FETCH_MAX_BYTES` | `2000000` | Maximum downloaded HTML size. |
| `CORS_ORIGINS` | FastAPI-only | Used by optional FastAPI app, not by `app.server`. |

## AI provider setup

No AI provider, deterministic analysis only:

```env
AI_PROVIDER=none
```

OpenAI:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.4-mini
```

Google Gemini:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

Local Ollama:

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

For Ollama, install and start Ollama separately, then pull a model, for example:

```powershell
ollama pull qwen2.5:7b
```
