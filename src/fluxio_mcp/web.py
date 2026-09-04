"""网页正文提取：httpx 抓取 + BeautifulSoup 清洗，输出对 LLM 友好的纯文本。"""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup, Tag

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; FluxioMcpBot/0.1; +https://github.com/IYABAO/fluxio-mcp)"
)

# 正文无关的标签，直接移除
_NOISE_TAGS = [
    "script", "style", "noscript", "template",
    "svg", "iframe", "nav", "header", "footer", "aside",
    "form", "button", "dialog", "figure", "figcaption",
]


def fetch_html(url: str, timeout: float = 15.0, max_bytes: int = 5_000_000) -> str:
    """抓取网页 HTML（带 UA、超时、体积上限）。"""
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": DEFAULT_UA},
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        if len(resp.content) > max_bytes:
            raise ValueError(f"页面过大（>{max_bytes // 1024 // 1024}MB），已拒绝抓取")
        # 优先按响应头 charset 解码，否则用 UTF-8（容错）
        return resp.text


def _clean_text(node: Tag) -> str:
    text = node.get_text(separator="\n", strip=True)
    # 合并连续空行
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def extract_web(html: str, url: str | None = None, max_chars: int = 8000) -> dict:
    """从 HTML 提取结构化正文信息。

    返回: {title, text, url}，text 为清洗后的正文纯文本（截断到 max_chars）。
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    # 优先取 main/article 区块；否则取 body（已去除噪音标签）
    main = soup.find("main") or soup.find("article") or soup.body or soup
    if not isinstance(main, Tag):
        main = soup

    text = _clean_text(main)

    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "\n…（正文已截断）"

    return {"title": title, "text": text, "url": url or ""}


def fetch_web(url: str, timeout: float = 15.0, max_chars: int = 8000) -> dict:
    """抓取并提取网页正文（组合 [fetch_html] 与 [extract_web]）。"""
    html = fetch_html(url, timeout=timeout)
    return extract_web(html, url=url, max_chars=max_chars)
