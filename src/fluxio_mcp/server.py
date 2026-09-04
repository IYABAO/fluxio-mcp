"""fluxio-mcp FastMCP Server：向 LLM 客户端暴露信息获取工具。"""

from __future__ import annotations

import sys
from typing import Annotated

import httpx
from fastmcp import FastMCP

from .rss import parse_rss
from .web import DEFAULT_UA, extract_web, fetch_html

mcp = FastMCP(
    "fluxio-mcp",
    instructions=(
        "信息获取工具集：解析 RSS/Atom 订阅源、抓取网页并提取正文。"
        "适用于让 LLM 读取资讯、博客、文档等网页内容。"
    ),
)

_MAX_RSS = 50
_MAX_HTML = 200_000  # 网页正文最大返回字符


@mcp.tool()
def fetch_rss(
    url: str,
    limit: Annotated[int, "最多返回文章数，1-50，默认 15"] = 15,
) -> str:
    """解析 RSS/Atom 订阅源，返回文章列表（标题/链接/发布时间/摘要）。

    参数:
        url: RSS/Atom 订阅地址，如 https://www.ruanyifeng.com/blog/atom.xml
        limit: 最多返回的文章条数

    返回:
        纯文本文章列表，每篇包含 标题、链接、发布时间、摘要。
    """
    limit = max(1, min(int(limit), _MAX_RSS))
    try:
        xml = fetch_html(url)
    except httpx.HTTPError as e:
        return f"抓取订阅源失败：{type(e).__name__}: {e}"
    except ValueError as e:
        return f"抓取订阅源失败：{e}"

    articles = parse_rss(xml, limit=limit)
    if not articles:
        return "未解析到文章（请确认该地址是有效的 RSS/Atom 订阅源）"

    lines = [f"订阅源：{url}\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. {a.title}")
        lines.append(f"   链接：{a.link}")
        if a.pub_date:
            lines.append(f"   时间：{a.pub_date}")
        if a.summary:
            summary = a.summary.replace("\n", " ")
            lines.append(f"   摘要：{summary[:200]}")
    return "\n".join(lines)


@mcp.tool()
def fetch_web(
    url: str,
    max_chars: Annotated[int, "返回正文最大字符数，500-200000，默认 8000"] = 8000,
) -> str:
    """抓取一个网页并提取正文纯文本（自动去除导航/脚本/样式等噪音）。

    参数:
        url: 网页地址，如 https://www.plbear.com/
        max_chars: 返回正文的最大字符数

    返回:
        页面标题 + 正文纯文本（适合喂给 LLM 阅读）。
    """
    max_chars = max(500, min(int(max_chars), _MAX_HTML))
    try:
        html = fetch_html(url)
        info = extract_web(html, url=url, max_chars=max_chars)
    except httpx.HTTPError as e:
        return f"抓取网页失败：{type(e).__name__}: {e}"
    except ValueError as e:
        return f"抓取网页失败：{e}"

    title = info["title"]
    text = info["text"]
    if not text:
        return "未能提取到正文（页面可能为 JS 动态渲染或反爬）"

    head = f"标题：{title}\n来源：{url}\n\n"
    return head + text


@mcp.resource("rss://{url}")
def rss_resource(url: str) -> str:
    """RSS 订阅源资源：`rss://<订阅地址>` 返回最近 15 篇文章。"""
    return fetch_rss(url, limit=15)


def main() -> None:
    """CLI 入口：默认 stdio 模式（供 Claude Desktop / Cursor 等 MCP 客户端调用）。"""
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
