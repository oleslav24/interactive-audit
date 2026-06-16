from __future__ import annotations

from .domain import PageFeatures, PageSnapshot, RubricResult


def build_payload(snapshot: PageSnapshot, features: PageFeatures, rubric: RubricResult) -> dict:
    return {
        "page": snapshot.public_dict(),
        "features": features.as_dict(),
        "rubric": rubric.as_dict(),
    }


def build_heuristic_report(snapshot: PageSnapshot, features: PageFeatures, rubric: RubricResult) -> dict:
    weak_criteria = [item for item in rubric.criteria if item.score <= 3]
    strong_criteria = [item for item in rubric.criteria if item.score >= 4]
    summary = (
        f"Страница получила {rubric.overall_score} из 5 по методической рубрике. "
        f"Обнаружено {features.word_count} слов, {features.interactive_elements_count} интерактивных элементов, "
        f"{features.images_count} изображений и "
        f"{features.videos_count + features.audios_count + features.iframes_count} мультимедийных встраиваний."
    )

    return {
        "summary": summary,
        "advantages": [
            finding
            for criterion in strong_criteria
            for finding in criterion.findings[:1]
        ][:6],
        "problems": [
            finding
            for criterion in weak_criteria
            for finding in criterion.findings[:1]
        ][:8],
        "recommendations": rubric.recommendations,
        "method_note": (
            "Автоматическая оценка является первичным аудитом. Финальный экспертный вывод "
            "желательно дополнить просмотром desktop/mobile-версий и UX-тестом по сценариям T1-T4."
        ),
        "source": {
            "requested_url": snapshot.requested_url,
            "final_url": snapshot.final_url,
            "title": features.title,
            "description": features.description,
        },
    }
