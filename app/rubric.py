from __future__ import annotations

from .domain import CriterionResult, PageFeatures, PageSnapshot, RubricResult


RUBRIC_DEFINITION = [
    {
        "key": "visual_structure",
        "name": "Визуальная структура и композиция",
        "description": "Иерархия заголовков, сканируемость, смысловые блоки и композиционная ясность.",
    },
    {
        "key": "navigation_control",
        "name": "Навигация и контроль пользователя",
        "description": "Наличие навигационных ориентиров, внутренних переходов и возможности вернуться к смысловым блокам.",
    },
    {
        "key": "interactivity_feedback",
        "name": "Интерактивность и обратная связь",
        "description": "Наличие интерактивных элементов, понятность аффордансов и базовая доступность элементов управления.",
    },
    {
        "key": "multimedia_cognition",
        "name": "Мультимедиа и когнитивная нагрузка",
        "description": "Уместность медиа, отсутствие навязчивого автозапуска, сохранение контроля пользователя.",
    },
    {
        "key": "accessibility",
        "name": "Доступность",
        "description": "Язык документа, alt-тексты, подписи интерактивных элементов, ARIA и базовая инклюзивность.",
    },
    {
        "key": "adaptability_technical",
        "name": "Адаптивность и техническая устойчивость",
        "description": "Viewport, CSS media queries, скорость ответа, зависимость от JavaScript.",
    },
    {
        "key": "cognitive_transparency",
        "name": "Когнитивная прозрачность пользовательского пути",
        "description": "Снижение неопределенности: понятные заголовки, отсутствие перегрузки, предсказуемость сценария.",
    },
]


def clamp_score(score: int) -> int:
    return max(1, min(5, score))


def _criterion(
    key: str,
    name: str,
    score: int,
    findings: list[str],
    recommendations: list[str],
    evidence: dict[str, object],
) -> CriterionResult:
    return CriterionResult(
        key=key,
        name=name,
        score=clamp_score(score),
        findings=findings,
        recommendations=recommendations,
        evidence=evidence,
    )


def evaluate_page(features: PageFeatures, snapshot: PageSnapshot | None = None) -> RubricResult:
    criteria = [
        _visual_structure(features),
        _navigation_control(features),
        _interactivity_feedback(features),
        _multimedia_cognition(features),
        _accessibility(features),
        _adaptability_technical(features, snapshot),
        _cognitive_transparency(features),
    ]

    overall = round(sum(item.score for item in criteria) / len(criteria), 2)
    strengths = [
        f"{item.name}: {item.findings[0]}"
        for item in criteria
        if item.score >= 4 and item.findings
    ]
    weaknesses = [
        f"{item.name}: {item.findings[0]}"
        for item in criteria
        if item.score <= 2 and item.findings
    ]
    recommendations: list[str] = []
    for item in sorted(criteria, key=lambda criterion: criterion.score):
        for recommendation in item.recommendations:
            if recommendation not in recommendations:
                recommendations.append(recommendation)
            if len(recommendations) >= 8:
                break
        if len(recommendations) >= 8:
            break

    return RubricResult(
        overall_score=overall,
        criteria=criteria,
        strengths=strengths[:6],
        weaknesses=weaknesses[:6],
        recommendations=recommendations,
    )


def _visual_structure(features: PageFeatures) -> CriterionResult:
    score = 3
    findings: list[str] = []
    recommendations: list[str] = []
    h1_count = len(features.headings.get("h1", []))
    h2_count = len(features.headings.get("h2", []))

    if h1_count == 1:
        score += 1
        findings.append("Страница имеет один главный заголовок, что помогает сформировать точку входа.")
    elif h1_count == 0:
        score -= 1
        findings.append("Не найден главный заголовок H1, из-за чего первый смысловой уровень может быть неочевиден.")
        recommendations.append("Добавить один выразительный H1, отражающий тему и назначение издания.")
    else:
        score -= 1
        findings.append("Найдено несколько H1, иерархия первого уровня может быть размытой.")
        recommendations.append("Оставить один H1, а остальные крупные заголовки перевести на уровень H2/H3.")

    if h2_count >= 3:
        score += 1
        findings.append("Есть несколько H2-разделов, материал потенциально пригоден для сканирования.")
    elif features.word_count > 700:
        score -= 1
        findings.append("При заметном объеме текста найдено мало H2-разделов.")
        recommendations.append("Разбить длинный материал на смысловые разделы с подзаголовками и якорями.")

    if features.word_count < 80:
        score -= 1
        findings.append("Текстовой контент слишком мал для экспертной оценки содержательной структуры.")
    elif features.estimated_reading_time_min >= 5 and h2_count < 3:
        recommendations.append("Для длинного чтения добавить оглавление и визуальные маркеры разделов.")

    return _criterion(
        "visual_structure",
        "Визуальная структура и композиция",
        score,
        findings or ["Структура страницы обнаружена, но требует дополнительной экспертной проверки."],
        recommendations,
        {"h1_count": h1_count, "h2_count": h2_count, "word_count": features.word_count},
    )


def _navigation_control(features: PageFeatures) -> CriterionResult:
    score = 3
    findings: list[str] = []
    recommendations: list[str] = []

    if features.nav_count:
        score += 1
        findings.append("Найден навигационный блок, пользователь получает ориентир в структуре.")
    else:
        score -= 1
        findings.append("Не найден явный навигационный блок.")
        recommendations.append("Добавить понятную навигацию или оглавление для восстановления маршрута чтения.")

    if features.anchors_count >= 3:
        score += 1
        findings.append("Есть внутренние якорные ссылки, что поддерживает быстрый переход к разделам.")
    elif features.word_count > 900:
        score -= 1
        findings.append("Для длинного материала обнаружено мало внутренних переходов.")
        recommendations.append("Для многостраничного или длинного лонгрида добавить якорное оглавление.")

    if features.links_count > 120:
        score -= 1
        findings.append("Слишком много ссылок может повышать количество точек принятия решения.")
        recommendations.append("Сгруппировать второстепенные ссылки и оставить основные сценарии видимыми.")

    return _criterion(
        "navigation_control",
        "Навигация и контроль пользователя",
        score,
        findings or ["Навигационная насыщенность находится на среднем уровне."],
        recommendations,
        {
            "nav_count": features.nav_count,
            "links_count": features.links_count,
            "anchors_count": features.anchors_count,
        },
    )


def _interactivity_feedback(features: PageFeatures) -> CriterionResult:
    score = 3
    findings: list[str] = []
    recommendations: list[str] = []

    if features.interactive_elements_count >= 8:
        score += 1
        findings.append("Страница содержит заметное количество интерактивных элементов.")
    elif features.interactive_elements_count <= 2:
        score -= 1
        findings.append("Интерактивных элементов мало для продукта, заявленного как интерактивное издание.")
        recommendations.append("Добавить осмысленные интерактивные элементы: тесты, карты, фильтры, управляемые галереи.")

    unlabeled_total = features.unlabeled_buttons_count + features.unlabeled_links_count
    if unlabeled_total:
        score -= 1
        findings.append("Обнаружены интерактивные элементы без доступного текстового названия.")
        recommendations.append("Добавить текст, aria-label или title для кнопок и ссылок без видимой подписи.")
    else:
        score += 1
        findings.append("Не обнаружены кнопки и ссылки без доступного текстового названия.")

    if features.onclick_handlers_count > features.buttons_count + 5:
        score -= 1
        findings.append("Много обработчиков onclick вне стандартных кнопок может создавать неочевидные аффордансы.")
        recommendations.append("Оформить кликабельные области как кнопки/ссылки с явными состояниями и подписями.")

    return _criterion(
        "interactivity_feedback",
        "Интерактивность и обратная связь",
        score,
        findings,
        recommendations,
        {
            "interactive_elements_count": features.interactive_elements_count,
            "unlabeled_buttons_count": features.unlabeled_buttons_count,
            "unlabeled_links_count": features.unlabeled_links_count,
            "onclick_handlers_count": features.onclick_handlers_count,
        },
    )


def _multimedia_cognition(features: PageFeatures) -> CriterionResult:
    score = 3
    findings: list[str] = []
    recommendations: list[str] = []
    media_total = features.videos_count + features.audios_count + features.iframes_count
    autoplay_total = features.videos_autoplay_count + features.audios_autoplay_count

    if media_total:
        score += 1
        findings.append("Найдены мультимедийные элементы, которые могут усиливать вовлеченность.")
    else:
        findings.append("Мультимедийные элементы не обнаружены или не представлены в исходном HTML.")
        recommendations.append("Если задача издания требует вовлечения, добавить мультимедиа как смысловую опору, а не как декор.")

    if autoplay_total:
        score -= 2
        findings.append("Обнаружен автозапуск аудио/видео, который может нарушать контроль пользователя.")
        recommendations.append("Отключить autoplay и запускать медиа по инициативе пользователя.")
    elif media_total:
        score += 1
        findings.append("Автозапуск медиа не обнаружен, контроль пользователя сохранен.")

    if media_total > 12 and features.word_count < 800:
        score -= 1
        findings.append("Медиа много относительно объема текста, возможна конкуренция каналов восприятия.")
        recommendations.append("Проверить, добавляет ли каждый медиаэлемент смысл, и убрать декоративные повторы.")

    return _criterion(
        "multimedia_cognition",
        "Мультимедиа и когнитивная нагрузка",
        score,
        findings,
        recommendations,
        {"media_total": media_total, "autoplay_total": autoplay_total},
    )


def _accessibility(features: PageFeatures) -> CriterionResult:
    score = 3
    findings: list[str] = []
    recommendations: list[str] = []

    if features.language:
        score += 1
        findings.append("У документа указан язык, это помогает экранным чтецам.")
    else:
        score -= 1
        findings.append("Не указан язык документа.")
        recommendations.append("Добавить атрибут lang на html, например lang=\"ru\".")

    if features.images_count:
        missing_ratio = features.images_without_alt / features.images_count
        if missing_ratio == 0:
            score += 1
            findings.append("Все изображения имеют alt-текст.")
        elif missing_ratio > 0.3:
            score -= 1
            findings.append("У значительной части изображений отсутствует alt-текст.")
            recommendations.append("Добавить содержательные alt-тексты для изображений, несущих смысл.")
        else:
            findings.append("Часть изображений не имеет alt-текста.")
            recommendations.append("Проверить alt-тексты у иллюстраций и инфографики.")

    if features.aria_attributes_count:
        findings.append("Найдены ARIA-атрибуты, доступность частично проработана.")
    elif features.interactive_elements_count > 10:
        score -= 1
        findings.append("При заметной интерактивности ARIA-атрибуты не обнаружены.")
        recommendations.append("Проверить интерактивные компоненты на поддержку клавиатуры и экранных чтецов.")

    if features.unlabeled_buttons_count:
        score -= 1

    return _criterion(
        "accessibility",
        "Доступность",
        score,
        findings,
        recommendations,
        {
            "language": features.language,
            "images_count": features.images_count,
            "images_without_alt": features.images_without_alt,
            "aria_attributes_count": features.aria_attributes_count,
        },
    )


def _adaptability_technical(features: PageFeatures, snapshot: PageSnapshot | None) -> CriterionResult:
    score = 3
    findings: list[str] = []
    recommendations: list[str] = []

    if features.has_viewport_meta:
        score += 1
        findings.append("Найден meta viewport, страница подготовлена к мобильному отображению.")
    else:
        score -= 1
        findings.append("Не найден meta viewport.")
        recommendations.append("Добавить meta viewport и проверить мобильную версию.")

    if features.css_media_queries_count:
        score += 1
        findings.append("В CSS обнаружены media queries, есть признаки адаптивной верстки.")
    else:
        recommendations.append("Добавить адаптивные состояния для мобильных и планшетных экранов.")

    if snapshot and snapshot.elapsed_ms > 3000:
        score -= 1
        findings.append("Первичная загрузка HTML заняла больше 3 секунд.")
        recommendations.append("Проверить вес страницы, изображения, видео и блокирующие скрипты.")

    if features.scripts_count > 35:
        score -= 1
        findings.append("Обнаружено много script-тегов, возможны риски производительности и поддержки.")
        recommendations.append("Сократить лишние скрипты и отложить необязательные сценарии.")

    if features.noscript_present:
        findings.append("Есть noscript-блок, предусмотрен сценарий без JavaScript.")

    return _criterion(
        "adaptability_technical",
        "Адаптивность и техническая устойчивость",
        score,
        findings,
        recommendations,
        {
            "has_viewport_meta": features.has_viewport_meta,
            "css_media_queries_count": features.css_media_queries_count,
            "scripts_count": features.scripts_count,
            "elapsed_ms": snapshot.elapsed_ms if snapshot else None,
        },
    )


def _cognitive_transparency(features: PageFeatures) -> CriterionResult:
    score = 3
    findings: list[str] = []
    recommendations: list[str] = []

    heading_count = sum(len(items) for items in features.headings.values())
    autoplay_total = features.videos_autoplay_count + features.audios_autoplay_count
    interactive_density = features.interactive_elements_count / max(features.word_count / 500, 1)

    if heading_count >= 4:
        score += 1
        findings.append("Заголовки создают несколько смысловых опор для ориентации.")
    else:
        score -= 1
        findings.append("Смысловых опор мало: пользователь может тратить усилие на понимание структуры.")
        recommendations.append("Добавить подзаголовки, оглавление и визуальные маркеры ключевых блоков.")

    if autoplay_total:
        score -= 1
        findings.append("Автозапуск повышает внешний когнитивный шум.")

    if interactive_density > 20:
        score -= 1
        findings.append("Высокая плотность интерактивных элементов может увеличивать число решений пользователя.")
        recommendations.append("Развести основные и второстепенные действия, убрать неоднозначные кликабельные области.")
    elif features.interactive_elements_count and heading_count >= 4:
        score += 1
        findings.append("Интерактивность сочетается со структурными ориентирами.")

    return _criterion(
        "cognitive_transparency",
        "Когнитивная прозрачность пользовательского пути",
        score,
        findings,
        recommendations,
        {
            "heading_count": heading_count,
            "interactive_density_per_500_words": round(interactive_density, 2),
            "autoplay_total": autoplay_total,
        },
    )
