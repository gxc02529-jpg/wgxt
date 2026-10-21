# -*- coding: utf-8 -*-
"""文稿富文本允许列表清洗，统一阻断存储型 XSS。"""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit


class _ArticleHTMLSanitizer(HTMLParser):
    """保留编辑器常用结构，删除危险节点、事件属性和不安全 URL。"""

    ALLOWED_TAGS = {
        "a", "b", "blockquote", "br", "code", "div", "em", "figcaption",
        "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img",
        "li", "ol", "p", "pre", "s", "span", "strong", "table", "tbody",
        "td", "th", "thead", "tr", "u", "ul",
    }
    VOID_TAGS = {"br", "hr", "img"}
    BLOCKED_CONTENT_TAGS = {
        "applet", "audio", "canvas", "embed", "form", "iframe", "math", "object",
        "script", "style", "svg", "template", "video",
    }
    ALIGN_VALUES = {"left", "center", "right", "justify"}
    TARGET_VALUES = {"_blank", "_self"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.open_tags: list[str] = []
        self.blocked_tags: list[str] = []

    @staticmethod
    def _safe_url(value: str, *, image: bool) -> bool:
        """只接受 HTTP(S) 与普通相对地址；链接额外允许邮件和电话协议。"""
        normalized = re.sub(r"[\x00-\x20\x7f]+", "", value).casefold()
        if not normalized or normalized.startswith("//"):
            return False
        parsed = urlsplit(normalized)
        if parsed.scheme:
            allowed = {"http", "https"} if image else {"http", "https", "mailto", "tel"}
            return parsed.scheme in allowed
        return True

    @staticmethod
    def _numeric_span(value: str) -> bool:
        return value.isdigit() and 1 <= int(value) <= 100

    def _clean_attributes(self, tag: str, attrs) -> list[tuple[str, str]]:
        raw = {str(name).casefold(): value for name, value in attrs if name and value is not None}
        cleaned: list[tuple[str, str]] = []

        title = raw.get("title", "").strip()
        if title:
            cleaned.append(("title", title[:300]))

        align = raw.get("align", "").casefold()
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th"} and align in self.ALIGN_VALUES:
            cleaned.append(("align", align))

        if tag == "a":
            href = raw.get("href", "").strip()
            if href and self._safe_url(href, image=False):
                cleaned.append(("href", href))
            target = raw.get("target", "").casefold()
            if target in self.TARGET_VALUES:
                cleaned.append(("target", target))
                if target == "_blank":
                    cleaned.append(("rel", "noopener noreferrer"))

        if tag == "img":
            src = raw.get("src", "").strip()
            if src and self._safe_url(src, image=True):
                cleaned.append(("src", src))
            alt = raw.get("alt", "").strip()
            if alt:
                cleaned.append(("alt", alt[:500]))
            for name in ("width", "height"):
                value = raw.get(name, "").strip()
                if value.isdigit() and 1 <= int(value) <= 10000:
                    cleaned.append((name, value))

        if tag in {"td", "th"}:
            for name in ("colspan", "rowspan"):
                value = raw.get(name, "").strip()
                if self._numeric_span(value):
                    cleaned.append((name, value))
        return cleaned

    @staticmethod
    def _render_start_tag(tag: str, attrs: list[tuple[str, str]]) -> str:
        suffix = "".join(
            f' {name}="{html.escape(value, quote=True)}"' for name, value in attrs
        )
        return f"<{tag}{suffix}>"

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized = tag.casefold()
        if self.blocked_tags:
            if normalized == self.blocked_tags[-1]:
                self.blocked_tags.append(normalized)
            return
        if normalized in self.BLOCKED_CONTENT_TAGS:
            self.blocked_tags.append(normalized)
            return
        if normalized not in self.ALLOWED_TAGS:
            return
        self.parts.append(self._render_start_tag(normalized, self._clean_attributes(normalized, attrs)))
        if normalized not in self.VOID_TAGS:
            self.open_tags.append(normalized)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if self.blocked_tags:
            if normalized == self.blocked_tags[-1]:
                self.blocked_tags.pop()
            return
        if normalized not in self.open_tags:
            return
        while self.open_tags:
            current = self.open_tags.pop()
            self.parts.append(f"</{current}>")
            if current == normalized:
                break

    def handle_data(self, data: str) -> None:
        if not self.blocked_tags:
            self.parts.append(html.escape(data, quote=False))

    def get_html(self) -> str:
        while self.open_tags:
            self.parts.append(f"</{self.open_tags.pop()}>")
        return "".join(self.parts).strip()


def sanitize_article_html(value: str | None) -> str:
    """返回可安全交给前端 `v-html` 渲染的文稿 HTML。"""
    if not value:
        return ""
    parser = _ArticleHTMLSanitizer()
    try:
        parser.feed(str(value))
        parser.close()
    except (TypeError, ValueError):
        return ""
    return parser.get_html()
