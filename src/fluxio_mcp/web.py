"""网页正文提取：httpx 抓取 + BeautifulSoup 清洗，输出对 LLM 友好的纯文本。

抓取层做了四件事，避免"偶发失败被当成源不可用"：
1. 分级超时：连接 5s，读取按调用方传入（默认 15s）
2. 瞬时错误重试：网络错误 / 超时 / 429 / 5xx，指数退避，默认 2 次
3. 流式读取，超过 max_bytes 立即中止，不把大文件读进内存
4. 编码回退：响应头 charset 优先，其次 UTF-8，最后 GB18030
"""

from __future__ import annotations

import re
import time

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

# 值得重试的状态码：限流与服务端瞬时故障
_RETRY_STATUS = {429, 500, 502, 503, 504}

# 值得重试的传输层异常
_RETRY_EXCEPTIONS = (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)

_CONNECT_TIMEOUT = 5.0
_DEFAULT_BACKOFF = 0.4


class _RetryableStatus(Exception):
    """可重试的 HTTP 状态码（内部信号，不外抛给调用方）。"""

    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


def _timeout(value: float | httpx.Timeout) -> httpx.Timeout:
    """把秒数转成分级超时；已经是 Timeout 对象则原样使用。"""
    if isinstance(value, httpx.Timeout):
        return value
    seconds = float(value)
    return httpx.Timeout(
        connect=min(_CONNECT_TIMEOUT, seconds),
        read=seconds,
        write=seconds,
        pool=min(_CONNECT_TIMEOUT, seconds),
    )


def _decode_body(content: bytes, charset: str | None) -> str:
    """按 charset → UTF-8 → GB18030 的顺序解码，全失败才容错返回。"""
    candidates = [charset] if charset else []
    candidates += ["utf-8", "gb18030"]
    for encoding in candidates:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


def fetch_html(
    url: str,
    timeout: float | httpx.Timeout = 15.0,
    max_bytes: int = 5_000_000,
    retries: int = 2,
    backoff: float = _DEFAULT_BACKOFF,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """抓取网页 HTML（带 UA、分级超时、体积上限、瞬时错误重试）。

    Args:
        url: 网页地址
        timeout: 读取超时秒数，或完整的 httpx.Timeout
        max_bytes: 响应体上限，超过即中止并抛 ValueError
        retries: 瞬时错误重试次数（0 表示不重试）
        backoff: 首次退避秒数，之后按 2 的幂递增
        transport: 自定义 httpx transport（测试注入用）

    Raises:
        ValueError: 页面过大或状态码重试耗尽
        httpx.HTTPError: 不可重试的状态码或重试耗尽的网络错误
    """
    retries = max(0, int(retries))
    timeout_obj = _timeout(timeout)

    with httpx.Client(
        timeout=timeout_obj,
        follow_redirects=True,
        headers={"User-Agent": DEFAULT_UA},
        transport=transport,
    ) as client:
        last_reason = ""
        for attempt in range(retries + 1):
            try:
                with client.stream("GET", url) as resp:
                    if resp.status_code in _RETRY_STATUS and attempt < retries:
                        raise _RetryableStatus(resp.status_code)
                    resp.raise_for_status()

                    body = bytearray()
                    for chunk in resp.iter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise ValueError(
                                f"页面过大（>{max_bytes // 1024 // 1024}MB），已拒绝抓取"
                            )

                    return _decode_body(bytes(body), resp.charset_encoding)
            except _RetryableStatus as exc:
                last_reason = str(exc)
                if attempt >= retries:
                    raise ValueError(
                        f"抓取失败：{last_reason}（已重试 {retries} 次）"
                    ) from None
            except _RETRY_EXCEPTIONS as exc:
                last_reason = f"{type(exc).__name__}: {exc}"
                if attempt >= retries:
                    raise
            if backoff:
                time.sleep(backoff * (2 ** attempt))

    # 循环只会在重试次数为负数时走到这里，正常不可达
    raise ValueError(f"抓取失败：{last_reason}")


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
