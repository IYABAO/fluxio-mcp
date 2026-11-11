import httpx
import pytest

from fluxio_mcp.web import extract_web, fetch_html
HTML = """<!DOCTYPE html>
<html><head><title>示例页面</title>
<style>body{color:red}</style>
</head><body>
<nav><a href="#">导航</a></nav>
<main>
  <h1>正文标题</h1>
  <p>第一段正文内容。</p>
  <p>第二段正文，包含
     换行。</p>
</main>
<footer>版权信息</footer>
<script>alert(1)</script>
</body></html>
"""


def test_extract_title_and_text():
    info = extract_web(HTML, url="https://example.com/")
    assert info["title"] == "示例页面"
    assert info["url"] == "https://example.com/"
    assert "正文标题" in info["text"]
    assert "第一段正文内容" in info["text"]
    assert "第二段正文" in info["text"]


def test_noise_removed():
    info = extract_web(HTML)
    # 导航、页脚、脚本、样式内容都被移除
    assert "导航" not in info["text"]
    assert "版权信息" not in info["text"]
    assert "alert(1)" not in info["text"]
    assert "color:red" not in info["text"]


def test_max_chars_truncates():
    long_html = "<html><body><main>" + "A" * 5000 + "</main></body></html>"
    info = extract_web(long_html, max_chars=100)
    assert len(info["text"]) <= 110  # 100 + 截断提示


def test_empty_body():
    info = extract_web("<html><head><title>空</title></head><body></body></html>")
    assert info["title"] == "空"
    assert info["text"] == ""


def _transport(handler):
    return httpx.MockTransport(handler)


def test_fetch_html_retries_on_503():
    calls = []

    def handler(request):
        calls.append(request.url)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, content="<html><body>恢复</body></html>".encode())

    html = fetch_html(
        "https://example.com/", retries=2, backoff=0, transport=_transport(handler)
    )
    assert "恢复" in html
    assert len(calls) == 2


def test_fetch_html_does_not_retry_404():
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(404)

    with pytest.raises(httpx.HTTPStatusError):
        fetch_html(
            "https://example.com/404", retries=2, backoff=0, transport=_transport(handler)
        )
    assert len(calls) == 1


def test_fetch_html_rejects_oversized_body_without_retry():
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, content=b"x" * 500)

    with pytest.raises(ValueError, match="页面过大"):
        fetch_html(
            "https://example.com/big",
            max_bytes=100,
            retries=2,
            backoff=0,
            transport=_transport(handler),
        )
    assert len(calls) == 1


def test_fetch_html_uses_charset_header():
    content = "中文正文".encode("gbk")

    def handler(request):
        return httpx.Response(
            200,
            content=content,
            headers={"content-type": "text/html; charset=gbk"},
        )

    html = fetch_html("https://example.com/", transport=_transport(handler))
    assert "中文正文" in html


def test_fetch_html_falls_back_to_gb18030_without_charset():
    content = "中文正文".encode("gbk")

    def handler(request):
        return httpx.Response(200, content=content)

    html = fetch_html("https://example.com/", transport=_transport(handler))
    assert "中文正文" in html
