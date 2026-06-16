from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=3, description="URL анализируемого интерактивного издания.")
    use_ai: bool = Field(True, description="Запрашивать ли AI-отчет через OpenAI.")
    include_features: bool = Field(True, description="Возвращать ли извлеченные признаки HTML.")


class AnalyzeResponse(BaseModel):
    status: str
    page: dict
    rubric: dict
    heuristic_report: dict
    ai: dict
    features: dict | None = None
