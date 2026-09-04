"""RSS 2.0 / Atom 订阅源解析（纯标准库，无第三方依赖）。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Article:
    """单条订阅文章。"""

    title: str
    link: str
    pub_date: str
    summary: str


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
    return (
        _txt(item.find("description"))
        or _txt(item.find("summary"))
        or _txt(item.find("content"))
    )


def parse_rss(xml_text: str, limit: int = 20) -> list[Article]:
    """解析 RSS 2.0 / Atom 文本，返回最多 `limit` 篇文章。

    同时兼容 RSS 的 `<item>` 与 Atom 的 `<entry>`；解析失败返回空列表。
    """
    try:
        root = _strip_ns(ET.fromstring(xml_text))
    except ET.ParseError:
        return []

    items = root.findall(".//item") or root.findall(".//entry")
    articles: list[Article] = []
    for item in items:
        title = _txt(item.find("title"))
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
