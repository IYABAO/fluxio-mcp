"""网页搜索：Bing 为主端点（国内可直连、免 Key），DuckDuckGo 为海外降级。"""

from __future__ import annotations

import urllib.parse

import httpx
from bs4 import BeautifulSoup

# 浏览器 UA：公开搜索端点常规请求（Bing/DuckDuckGo 对爬虫 UA 会拦截或降级）
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# 主端点 Bing（国内直连），降级端点 DuckDuckGo html
_SEARCH_ENDPOINTS = [
    ("bing", "https://www.bing.com/search"),
    ("duckduckgo", "https://html.duckduckgo.com/html/"),
]


def _fetch(url: str, timeout: float = 12.0) -> str | None:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    ) as client:
        resp = client.get(url)
        if resp.status_code != 200:
            return None
        return resp.text


def _parse_bing(html: str, max_results: int) -> list[dict]:
    """解析 Bing 结果页（li.b_algo）。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for li in soup.select("li.b_algo"):
        a = li.select_one("h2 a")
        if a is None:
            continue
        title = a.get_text(strip=True)
        href = a.get("href", "").strip()
        if not href or href.startswith(("javascript:", "#")):
            continue
        snippet_el = li.select_one("p") or li.select_one(".b_caption p")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _parse_duckduckgo(html: str, max_results: int) -> list[dict]:
    """解析 DuckDuckGo html 端点结果页（div.result，链接含 uddg 跳转）。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []
    for div in soup.select("div.result"):
        a = div.select_one("a.result__a")
        if a is None:
            continue
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if "uddg=" in href:
            href = urllib.parse.unquote(
                urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0]
            )
        snippet_el = div.select_one("a.result__snippet") or div.select_one("div.result__snippet")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def search_web(query: str, max_results: int = 8, timeout: float = 12.0) -> dict:
    """搜索网页，返回 标题/链接/摘要 列表（Bing 主端点，免 API Key）。

    Args:
        query: 搜索关键词
        max_results: 最多返回结果数（1-20，默认 8）

    Returns:
        {"query": ..., "results": [{title, url, snippet}, ...]}
    """
    max_results = max(1, min(int(max_results), 20))
    params = urllib.parse.urlencode({"q": query, "mkt": "zh-CN", "setlang": "zh-hans"})

    for engine, endpoint in _SEARCH_ENDPOINTS:
        try:
            html = _fetch(f"{endpoint}?{params}", timeout=timeout)
            if not html:
                continue
            results = (
                _parse_bing(html, max_results)
                if engine == "bing"
                else _parse_duckduckgo(html, max_results)
            )
            if results:
                return {"query": query, "results": results}
        except httpx.HTTPError:
            continue

    return {"query": query, "results": [], "error": "搜索服务暂不可用（Bing/DuckDuckGo 均失败或被拦截）"}
