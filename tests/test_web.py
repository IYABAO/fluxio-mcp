from fluxio_mcp.web import extract_web

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
