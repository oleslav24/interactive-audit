from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .fetcher import FetchError, URLValidationError, fetch_url
from .html_features import extract_features
from .llm import generate_ai_report
from .reporting import build_heuristic_report, build_payload
from .rubric import RUBRIC_DEFINITION, evaluate_page
from .schemas import AnalyzeRequest, AnalyzeResponse


settings = get_settings()

app = FastAPI(
    title="Expert Analysis Backend",
    version="0.1.0",
    description="Backend-прототип для экспертного анализа интерактивных многостраничных изданий.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "ai_enabled": settings.ai_enabled,
        "openai_model": settings.openai_model,
    }


@app.get("/api/rubric")
def rubric() -> dict:
    return {"criteria": RUBRIC_DEFINITION}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> dict:
    try:
        snapshot = fetch_url(
            request.url,
            timeout_seconds=settings.fetch_timeout_seconds,
            max_bytes=settings.fetch_max_bytes,
            allow_private=settings.allow_private_urls,
        )
    except URLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    features = extract_features(snapshot.html)
    rubric_result = evaluate_page(features, snapshot)
    payload = build_payload(snapshot, features, rubric_result)
    heuristic_report = build_heuristic_report(snapshot, features, rubric_result)

    ai_report = generate_ai_report(
        payload,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        enabled=request.use_ai and settings.ai_enabled,
    )

    return {
        "status": "ok",
        "page": payload["page"],
        "features": payload["features"] if request.include_features else None,
        "rubric": payload["rubric"],
        "heuristic_report": heuristic_report,
        "ai": {
            "used": ai_report.used,
            "model": ai_report.model,
            "report": ai_report.report,
            "error": ai_report.error,
        },
    }
