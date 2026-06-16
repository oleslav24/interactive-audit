from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class PageSnapshot:
    requested_url: str
    final_url: str
    status_code: int | None
    content_type: str
    html: str
    elapsed_ms: int
    fetched_at: str
    warnings: list[str] = field(default_factory=list)

    def public_dict(self) -> dict:
        data = asdict(self)
        data.pop("html", None)
        return data


@dataclass
class PageFeatures:
    title: str
    description: str
    language: str
    text_length: int
    word_count: int
    estimated_reading_time_min: int
    headings: dict[str, list[str]]
    links_count: int
    anchors_count: int
    buttons_count: int
    inputs_count: int
    forms_count: int
    images_count: int
    images_without_alt: int
    videos_count: int
    videos_autoplay_count: int
    audios_count: int
    audios_autoplay_count: int
    iframes_count: int
    scripts_count: int
    nav_count: int
    main_count: int
    footer_count: int
    has_viewport_meta: bool
    css_media_queries_count: int
    aria_attributes_count: int
    unlabeled_buttons_count: int
    unlabeled_links_count: int
    interactive_elements_count: int
    onclick_handlers_count: int
    noscript_present: bool
    total_tags_count: int
    evidence: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class CriterionResult:
    key: str
    name: str
    score: int
    findings: list[str]
    recommendations: list[str]
    evidence: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RubricResult:
    overall_score: float
    criteria: list[CriterionResult]
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]

    def as_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "criteria": [criterion.as_dict() for criterion in self.criteria],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
        }
