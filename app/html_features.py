from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

from .domain import PageFeatures


WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+(?:[-'][A-Za-zА-Яа-яЁё0-9]+)?")


def _attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {name.lower(): value or "" for name, value in attrs}


class FeatureHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.current_heading: str | None = None
        self.current_heading_parts: list[str] = []
        self.headings: dict[str, list[str]] = {f"h{i}": [] for i in range(1, 7)}
        self.in_title = False
        self.skip_text_depth = 0

        self.description = ""
        self.language = ""
        self.links_count = 0
        self.anchors_count = 0
        self.buttons_count = 0
        self.inputs_count = 0
        self.forms_count = 0
        self.images_count = 0
        self.images_without_alt = 0
        self.videos_count = 0
        self.videos_autoplay_count = 0
        self.audios_count = 0
        self.audios_autoplay_count = 0
        self.iframes_count = 0
        self.scripts_count = 0
        self.nav_count = 0
        self.main_count = 0
        self.footer_count = 0
        self.has_viewport_meta = False
        self.aria_attributes_count = 0
        self.unlabeled_buttons_count = 0
        self.unlabeled_links_count = 0
        self.interactive_elements_count = 0
        self.onclick_handlers_count = 0
        self.noscript_present = False
        self.total_tags_count = 0

        self._button_stack: list[dict[str, object]] = []
        self._link_stack: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = _attrs_dict(attrs)
        self.total_tags_count += 1

        if tag in {"script", "style"}:
            self.skip_text_depth += 1
        if tag == "noscript":
            self.noscript_present = True

        if "onclick" in attr:
            self.onclick_handlers_count += 1
        self.aria_attributes_count += sum(1 for name in attr if name.startswith("aria-"))

        role = attr.get("role", "").lower()
        if tag == "html":
            self.language = attr.get("lang", self.language).strip()
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = attr.get("name", "").lower()
            prop = attr.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.description = self.description or attr.get("content", "").strip()
            if name == "viewport":
                self.has_viewport_meta = True
        elif tag in self.headings:
            self.current_heading = tag
            self.current_heading_parts = []
        elif tag == "a":
            self.links_count += 1
            if attr.get("href", "").startswith("#"):
                self.anchors_count += 1
            self._link_stack.append(
                {
                    "has_label": bool(
                        attr.get("aria-label") or attr.get("title") or attr.get("aria-labelledby")
                    ),
                    "text": [],
                }
            )
        elif tag == "button":
            self.buttons_count += 1
            self._button_stack.append(
                {
                    "has_label": bool(
                        attr.get("aria-label") or attr.get("title") or attr.get("aria-labelledby")
                    ),
                    "text": [],
                }
            )
        elif tag == "input":
            self.inputs_count += 1
            input_type = attr.get("type", "").lower()
            if input_type in {"button", "submit", "reset"}:
                self.buttons_count += 1
                if not (attr.get("value") or attr.get("aria-label") or attr.get("title")):
                    self.unlabeled_buttons_count += 1
        elif tag == "form":
            self.forms_count += 1
        elif tag == "img":
            self.images_count += 1
            if not attr.get("alt", "").strip():
                self.images_without_alt += 1
        elif tag == "video":
            self.videos_count += 1
            if "autoplay" in attr:
                self.videos_autoplay_count += 1
        elif tag == "audio":
            self.audios_count += 1
            if "autoplay" in attr:
                self.audios_autoplay_count += 1
        elif tag == "iframe":
            self.iframes_count += 1
        elif tag == "script":
            self.scripts_count += 1
        elif tag == "nav" or role == "navigation":
            self.nav_count += 1
        elif tag == "main" or role == "main":
            self.main_count += 1
        elif tag == "footer":
            self.footer_count += 1

        if (
            tag in {"a", "button", "input", "select", "textarea", "details", "summary", "audio", "video"}
            or role in {"button", "link", "tab", "menuitem", "switch"}
            or "onclick" in attr
        ):
            self.interactive_elements_count += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self.skip_text_depth:
            self.skip_text_depth -= 1
        elif tag == "title":
            self.in_title = False
        elif tag == self.current_heading:
            text = " ".join(part.strip() for part in self.current_heading_parts if part.strip())
            if text:
                self.headings[tag].append(unescape(text)[:160])
            self.current_heading = None
            self.current_heading_parts = []
        elif tag == "button" and self._button_stack:
            state = self._button_stack.pop()
            text = " ".join(state["text"]).strip()
            if not state["has_label"] and not text:
                self.unlabeled_buttons_count += 1
        elif tag == "a" and self._link_stack:
            state = self._link_stack.pop()
            text = " ".join(state["text"]).strip()
            if not state["has_label"] and not text:
                self.unlabeled_links_count += 1

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if not clean:
            return
        if self.in_title:
            self.title_parts.append(clean)
        if self.current_heading:
            self.current_heading_parts.append(clean)
        if self._button_stack:
            self._button_stack[-1]["text"].append(clean)
        if self._link_stack:
            self._link_stack[-1]["text"].append(clean)
        if self.skip_text_depth == 0 and not self.in_title:
            self.text_parts.append(clean)


def extract_features(html: str) -> PageFeatures:
    parser = FeatureHTMLParser()
    parser.feed(html)
    parser.close()

    visible_text = unescape(" ".join(parser.text_parts))
    words = WORD_RE.findall(visible_text)
    word_count = len(words)
    reading_time = max(1, round(word_count / 180)) if word_count else 0
    css_media_queries = len(re.findall(r"@media\b", html, flags=re.IGNORECASE))
    title = " ".join(parser.title_parts).strip()

    return PageFeatures(
        title=title,
        description=parser.description,
        language=parser.language,
        text_length=len(visible_text),
        word_count=word_count,
        estimated_reading_time_min=reading_time,
        headings=parser.headings,
        links_count=parser.links_count,
        anchors_count=parser.anchors_count,
        buttons_count=parser.buttons_count,
        inputs_count=parser.inputs_count,
        forms_count=parser.forms_count,
        images_count=parser.images_count,
        images_without_alt=parser.images_without_alt,
        videos_count=parser.videos_count,
        videos_autoplay_count=parser.videos_autoplay_count,
        audios_count=parser.audios_count,
        audios_autoplay_count=parser.audios_autoplay_count,
        iframes_count=parser.iframes_count,
        scripts_count=parser.scripts_count,
        nav_count=parser.nav_count,
        main_count=parser.main_count,
        footer_count=parser.footer_count,
        has_viewport_meta=parser.has_viewport_meta,
        css_media_queries_count=css_media_queries,
        aria_attributes_count=parser.aria_attributes_count,
        unlabeled_buttons_count=parser.unlabeled_buttons_count,
        unlabeled_links_count=parser.unlabeled_links_count,
        interactive_elements_count=parser.interactive_elements_count,
        onclick_handlers_count=parser.onclick_handlers_count,
        noscript_present=parser.noscript_present,
        total_tags_count=parser.total_tags_count,
        evidence={
            "sample_h1": parser.headings.get("h1", [])[:3],
            "sample_h2": parser.headings.get("h2", [])[:6],
            "media_total": parser.videos_count + parser.audios_count + parser.iframes_count,
            "autoplay_total": parser.videos_autoplay_count + parser.audios_autoplay_count,
        },
    )
