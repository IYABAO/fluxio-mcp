"""HTML → Markdown 转换：保留标题层级/列表/代码块/链接/图片/表格等结构。"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

# 正文无关的标签，直接移除（与 web.py 保持同一套噪音策略）
_NOISE_TAGS = [
    "script", "style", "noscript", "template",
    "svg", "iframe", "nav", "header", "footer", "aside",
    "form", "button", "dialog",
]

_HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}

# 需要换行分隔的块级标签
_BLOCK_TAGS = {
    "p", "div", "section", "article", "main", "blockquote", "pre",
    "ul", "ol", "table", "li", "tr", "figure", "hr",
}

_INLINE_BOLD = {"strong", "b"}
_INLINE_ITALIC = {"em", "i"}


def _code_lang(node: Tag) -> str:
    """从 <pre><code class="language-xxx"> 提取代码语言。"""
    code = node.find("code")
    if code is None:
        return ""
    cls = code.get("class") or []
    for c in cls:
        if c.startswith("language-") or c.startswith("lang-"):
            return c.split("-", 1)[1]
    return ""


def _convert(node: Tag, in_pre: bool = False) -> str:
    """递归把节点树转换为 Markdown 文本。"""
    parts: list[str] = []

    for child in node.children:
        # 纯文本节点
        if isinstance(child, NavigableString):
            text = str(child)
            if in_pre:
                # 代码块内保留原文（去行尾空白）
                parts.append(text.rstrip())
            else:
                parts.append(text)
            continue

        if not isinstance(child, Tag):
            continue

        name = child.name.lower()

        # 代码块（pre 或 pre>code）
        if name == "pre":
            code = child.get_text()
            lang = _code_lang(child)
            fence = "```"
            parts.append(f"\n{fence}{lang}\n{code.rstrip()}\n{fence}\n")
            continue

        # 标题
        if name in _HEADING:
            inner = _convert(child).strip()
            parts.append(f"\n{_HEADING[name]} {inner}\n")
            continue

        # 列表
        if name in ("ul", "ol"):
            ordered = name == "ol"
            idx = 1
            for li in child.find_all("li", recursive=False):
                marker = f"{idx}. " if ordered else "- "
                parts.append(f"{marker}{_convert(li).strip()}\n")
                idx += 1
            continue

        # 引用
        if name == "blockquote":
            inner = _convert(child).strip().replace("\n", "\n> ")
            parts.append(f"\n> {inner}\n")
            continue

        # 行内元素
        if name in _INLINE_BOLD:
            inner = _convert(child).strip()
            parts.append(f"**{inner}**" if inner else "")
            continue
        if name in _INLINE_ITALIC:
            inner = _convert(child).strip()
            parts.append(f"*{inner}*" if inner else "")
            continue

        # 链接
        if name == "a":
            cls = child.get("class") or []
            # 跳过标题锚点链接（如主题生成的 headerlink "#"），避免标题尾部残留 "#"
            if "headerlink" in cls or "anchor" in cls:
                continue
            href = child.get("href", "").strip()
            inner = _convert(child).strip() or href
            if not href or href.startswith(("javascript:", "#")):
                parts.append(inner)
            else:
                parts.append(f"[{inner}]({href})")
            continue

        # 图片
        if name == "img":
            src = child.get("src") or child.get("data-src") or ""
            alt = child.get("alt", "").strip()
            if src:
                parts.append(f"![{alt}]({src})")
            elif alt:
                parts.append(alt)
            continue

        # 行内代码
        if name == "code" and not in_pre:
            parts.append(f"`{child.get_text()}`")
            continue

        # 换行
        if name == "br":
            parts.append("\n")
            continue

        # 表格：简化为 Markdown 表格
        if name == "table":
            md_table = _table_to_markdown(child)
            if md_table:
                parts.append(f"\n{md_table}\n")
            continue

        # 分隔线
        if name == "hr":
            parts.append("\n---\n")
            continue

        # 其他块级标签：递归并在块间补空行
        inner = _convert(child, in_pre=in_pre).strip()
        if name in _BLOCK_TAGS:
            if inner:
                parts.append(f"\n{inner}\n")
        else:
            parts.append(inner)

    return "".join(parts)


def _table_to_markdown(table: Tag) -> str:
    """HTML 表格 → Markdown 表格（仅基础支持）。"""
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = []
        for cell in tr.find_all(["th", "td"]):
            cells.append(_convert(cell).strip().replace("\n", " "))
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]

    lines = ["| " + " | ".join(rows[0]) + " |"]
    lines.append("| " + " | ".join(["---"] * width) + " |")
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def _collapse_blank(text: str) -> str:
    """合并多余空行（保留段落/块间的一个空行）。"""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def html_to_markdown(html: str) -> str:
    """HTML → Markdown。

    保留：标题层级、列表、代码块(带语言)、引用、链接、图片、粗斜体、表格；
    去除：导航/脚本/样式等噪音标签。
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    if not isinstance(main, Tag):
        main = soup

    md = _convert(main)
    return _collapse_blank(md)
