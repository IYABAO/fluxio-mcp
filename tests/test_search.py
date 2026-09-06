"""search_web 解析单测 + 真实网络端到端。"""

import pytest

from fluxio_mcp.search import (
    _parse_bing,
    _parse_duckduckgo,
    search_web,
)

BING_SAMPLE = """
<html><body>
<ol id="b_results">
<li class="b_algo">
  <h2><a href="https://example.com/blog">示例博客标题</a></h2>
  <div class="b_caption"><p>这是一段摘要内容</p></div>
</li>
<li class="b_algo">
  <h2><a href="https://example.org">第二个结果</a></h2>
  <p>第二个摘要</p>
</li>
</ol>
</body></html>
"""


def test_parse_bing():
    results = _parse_bing(BING_SAMPLE, max_results=5)
    assert len(results) == 2
    assert results[0]["title"] == "示例博客标题"
    assert results[0]["url"] == "https://example.com/blog"
    assert results[0]["snippet"] == "这是一段摘要内容"
    assert results[1]["url"] == "https://example.org"


def test_parse_bing_limit():
    results = _parse_bing(BING_SAMPLE, max_results=1)
    assert len(results) == 1


DUCKDUCKGO_SAMPLE = """
<html><body>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fblog&amp;rut=abc">示例博客</a>
  <a class="result__snippet">这是一段摘要内容</a>
</div>
<div class="result">
  <a class="result__a" href="https://example.org">第二个结果</a>
</div>
</body></html>
"""


def test_parse_duckduckgo_uddg_decode():
    results = _parse_duckduckgo(DUCKDUCKGO_SAMPLE, max_results=5)
    assert len(results) == 2
    assert results[0]["title"] == "示例博客"
    assert results[0]["url"] == "https://example.com/blog"
    assert results[0]["snippet"] == "这是一段摘要内容"


@pytest.mark.network
def test_search_web_real():
    """真实网络：Bing 搜索一个确定存在的词。"""
    data = search_web("golang 微服务", max_results=5)
    assert data["query"] == "golang 微服务"
    results = data.get("results")
    if results:
        assert all(r.get("title") and r.get("url") for r in results)
    else:
        # 允许网络/反爬降级：error 字段必须存在，不能静默空
        assert data.get("error")
