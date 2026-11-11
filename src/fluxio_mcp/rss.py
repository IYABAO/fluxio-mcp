"""RSS 2.0 / Atom 订阅源解析（纯标准库，无第三方依赖）。

解析失败必须能和"空订阅源"区分开：调用方需要知道是源坏了、拿到的是网页，
还是源本身没有条目。默认 `strict=False` 保持旧的空列表行为，`strict=True`
抛出 `RSSParseError` 并带上原因。
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


class RSSParseError(ValueError):
    """订阅源无法解析（非 XML、或是网页而非 feed）。"""


@dataclass
class Article:
    """单条订阅文章。"""

    title: str
    link: str
    pub_date: str
    summary: str


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _local(tag: str) -> str:
    """去掉 XML 命名空间前缀，如 `{http://www.w3.org/2005/Atom}title` -> `title`。"""
    return tag.rsplit("}", 1)[-1]


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if "}" in el.tag:
            el.tag = _local(el.tag)
    return root


def _txt(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def _plain(text: str) -> str:
    """摘要里常带 HTML 片段，去掉标签、反转义实体、压平空白。"""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _link(item: ET.Element) -> str:
    """取链接：RSS 用 `<link>text</link>`，Atom 用 `<link href="..."/>`。"""
    link = item.find("link")
    if link is None:
        return ""
    if link.get("href"):
        return link.get("href", "").strip()
    return _txt(link)


def _date(item: ET.Element) -> str:
    return _txt(item.find("pubDate")) or _txt(item.find("published")) or _txt(item.find("updated"))


def _summary(item: ET.Element) -> str:
    raw = (
        _txt(item.find("description"))
        or _txt(item.find("summary"))
        or _txt(item.find("content"))
    )
    return _plain(raw)


def _looks_like_html(xml_text: str) -> bool:
    head = xml_text.lstrip()[:200].lower()
    return head.startswith(("<!doctype html", "<html"))


def parse_rss(xml_text: str, limit: int = 20, strict: bool = False) -> list[Article]:
    """解析 RSS 2.0 / Atom 文本，返回最多 `limit` 篇文章。

    同时兼容 RSS 的 `<item>` 与 Atom 的 `<entry>`。

    Args:
        xml_text: 订阅源原文
        limit: 最多返回条数
        strict: True 时解析失败抛 RSSParseError，False 时返回空列表

    Raises:
        RSSParseError: strict=True 且内容不是合法 XML / 实际是网页
    """
    # 去掉 UTF-8 BOM：部分源站直接输出带 BOM 的 XML，ET 会报"declaration not at start"
    xml_text = xml_text.lstrip("\ufeff")

    if _looks_like_html(xml_text):
        if strict:
            raise RSSParseError("返回的是网页而不是 RSS/Atom（可能被反爬或被重定向到首页）")
        return []

    try:
        root = _strip_ns(ET.fromstring(xml_text))
    except ET.ParseError as exc:
        if strict:
            raise RSSParseError(f"XML 解析失败：{exc}") from exc
        return []

    items = root.findall(".//item") or root.findall(".//entry")
    articles: list[Article] = []
    for item in items:
        title = _plain(_txt(item.find("title")))
        link = _link(item)
        if not title or not link:
            continue
        articles.append(
            Article(
                title=title,
                link=link,
                pub_date=_date(item),
                summary=_summary(item),
            )
        )
        if len(articles) >= limit:
            break
    return articles
