"""批量网页抓取：一次处理多个 URL，单点失败不影响整体。"""

from __future__ import annotations

import httpx

from .markdown import html_to_markdown
from .web import extract_web, fetch_html


def fetch_urls(
    urls: list[str],
    mode: str = "text",
    max_chars: int = 3000,
    timeout: float = 15.0,
) -> dict:
    """批量抓取多个网页，返回 标题 + 正文摘要（text 或 markdown）。

    Args:
        urls: URL 列表（最多 5 个）
        mode: "text" 纯文本正文 | "markdown" Markdown 正文
        max_chars: 每个条目的最大字符数（500-20000）

    Returns:
        {"results": [{url, ok, title?, content?, error?}, ...]}
    """
    urls = [u.strip() for u in urls if u and u.strip()]
    urls = urls[:5]
    max_chars = max(500, min(int(max_chars), 20000))

    results: list[dict] = []
    for url in urls:
        entry: dict = {"url": url}
        try:
            html = fetch_html(url, timeout=timeout)
            if mode == "markdown":
                content = html_to_markdown(html)
                title = extract_web(html, url=url, max_chars=200)["title"]
            else:
                info = extract_web(html, url=url, max_chars=max_chars)
                title, content = info["title"], info["text"]
            if not content:
                entry.update(ok=False, error="未能提取到正文（可能为 JS 渲染或反爬）")
            else:
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n…（已截断）"
                entry.update(ok=True, title=title, content=content)
        except httpx.HTTPError as e:
            entry.update(ok=False, error=f"{type(e).__name__}: {e}")
        except ValueError as e:
            entry.update(ok=False, error=str(e))
        results.append(entry)
    return {"results": results}
