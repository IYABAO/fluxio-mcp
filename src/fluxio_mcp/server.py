"""fluxio-mcp FastMCP Server：向 LLM 客户端暴露信息获取工具。"""

from __future__ import annotations

import sys
from typing import Annotated

import httpx
from fastmcp import FastMCP

from .batch import fetch_urls as _fetch_urls
from .markdown import html_to_markdown
from .rss import RSSParseError, parse_rss
from .search import search_web as _search_web
from .web import DEFAULT_UA, extract_web, fetch_html

mcp = FastMCP(
    "fluxio-mcp",
    instructions=(
        "信息获取工具集：解析 RSS/Atom 订阅源、抓取网页并提取正文、"
        "网页转 Markdown、网页搜索。适用于让 LLM 读取资讯、博客、文档等网页内容。"
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

    try:
        articles = parse_rss(xml, limit=limit, strict=True)
    except RSSParseError as e:
        return f"解析订阅源失败：{e}"
    if not articles:
        return "订阅源可解析，但没有文章条目（可能是空源，或条目缺少标题/链接）"

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


@mcp.tool()
def fetch_web_md(
    url: str,
    max_chars: Annotated[int, "返回 Markdown 最大字符数，500-200000，默认 15000"] = 15000,
) -> str:
    """抓取一个网页并转换为 Markdown（保留标题层级/列表/代码块/链接/图片/表格）。

    参数:
        url: 网页地址，如 https://www.plbear.com/
        max_chars: 返回 Markdown 的最大字符数

    返回:
        页面标题 + Markdown 正文（比纯文本更适合喂给 LLM / 文档化场景）。
    """
    max_chars = max(500, min(int(max_chars), _MAX_HTML))
    try:
        html = fetch_html(url)
    except httpx.HTTPError as e:
        return f"抓取网页失败：{type(e).__name__}: {e}"
    except ValueError as e:
        return f"抓取网页失败：{e}"

    soup_md = html_to_markdown(html)
    if not soup_md:
        return "未能提取到正文（页面可能为 JS 动态渲染或反爬）"

    title = extract_web(html, url=url, max_chars=200)["title"]
    if len(soup_md) > max_chars:
        soup_md = soup_md[:max_chars] + "\n…（Markdown 已截断）"

    head = f"标题：{title}\n来源：{url}\n\n"
    return head + soup_md


@mcp.tool()
def search_web(
    query: str,
    max_results: Annotated[int, "最多返回结果数，1-20，默认 8"] = 8,
) -> str:
    """搜索网页，返回 标题/链接/摘要 列表（免 API Key，基于 DuckDuckGo）。

    参数:
        query: 搜索关键词
        max_results: 最多返回的结果条数

    返回:
        纯文本结果列表，每条包含 标题、链接、摘要。
    """
    data = _search_web(query, max_results=max_results)
    results = data.get("results", [])
    if not results:
        return data.get("error", f"未搜索到「{query}」相关结果")

    lines = [f"搜索：{query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   链接：{r['url']}")
        if r.get("snippet"):
            lines.append(f"   摘要：{r['snippet'][:200]}")
    return "\n".join(lines)


@mcp.tool()
def fetch_urls(
    urls: list[str],
    mode: Annotated[str, "输出格式：text=纯文本正文，markdown=Markdown正文"] = "text",
    max_chars: Annotated[int, "每个条目的最大字符数，500-20000，默认 3000"] = 3000,
) -> str:
    """批量抓取多个网页，返回每个的标题与正文摘要（单点失败不影响整体）。

    参数:
        urls: URL 列表（最多 5 个）
        mode: "text" 或 "markdown"
        max_chars: 每个条目的最大字符数

    返回:
        逐条列出每个 URL 的 标题 + 正文（失败的条目标注原因）。
    """
    data = _fetch_urls(urls, mode=mode, max_chars=max_chars)
    lines: list[str] = [f"批量抓取 {len(data['results'])} 个网页（模式：{mode}）\n"]
    for i, r in enumerate(data["results"], 1):
        if r.get("ok"):
            lines.append(f"{i}. ✅ {r['title']}")
            lines.append(f"   {r['url']}")
            lines.append(f"   {r['content'][:400]}")
        else:
            lines.append(f"{i}. ❌ {r['url']}")
            lines.append(f"   {r.get('error', '未知错误')}")
        lines.append("")
    return "\n".join(lines).rstrip()


@mcp.resource("rss://{url}")
def rss_resource(url: str) -> str:
    """RSS 订阅源资源：`rss://<订阅地址>` 返回最近 15 篇文章。"""
    return fetch_rss(url, limit=15)


def main() -> None:
    """CLI 入口：默认 stdio 模式（供 Claude Desktop / Cursor 等 MCP 客户端调用）。"""
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
