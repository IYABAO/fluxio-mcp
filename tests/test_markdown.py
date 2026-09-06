"""HTML → Markdown 转换单测。"""

from fluxio_mcp.markdown import html_to_markdown


def test_heading_hierarchy():
    html = "<h1>标题1</h1><h2>标题2</h2><h3>标题3</h3>"
    md = html_to_markdown(html)
    assert "# 标题1" in md
    assert "## 标题2" in md
    assert "### 标题3" in md


def test_list_ul_ol():
    html = "<ul><li>甲</li><li>乙</li></ul><ol><li>一</li><li>二</li></ol>"
    md = html_to_markdown(html)
    assert "- 甲" in md and "- 乙" in md
    assert "1. 一" in md and "2. 二" in md


def test_code_block_with_language():
    html = '<pre><code class="language-python">def f(): return 1</code></pre>'
    md = html_to_markdown(html)
    assert "```python" in md
    assert "def f(): return 1" in md
    assert "```" in md


def test_inline_code_and_bold():
    html = "<p>用 <code>go run</code> 和 <strong>并发</strong> 写 <em>优雅</em> 的代码</p>"
    md = html_to_markdown(html)
    assert "`go run`" in md
    assert "**并发**" in md
    assert "*优雅*" in md


def test_link_and_image():
    html = '<p>看 <a href="https://example.com">示例</a> <img src="/img/a.png" alt="架构图"/></p>'
    md = html_to_markdown(html)
    assert "[示例](https://example.com)" in md
    assert "![架构图](/img/a.png)" in md


def test_blockquote():
    html = "<blockquote><p>第一行</p><p>第二行</p></blockquote>"
    md = html_to_markdown(html)
    assert "> 第一行" in md
    assert "> 第二行" in md


def test_table():
    html = "<table><tr><th>名称</th><th>值</th></tr><tr><td>A</td><td>1</td></tr></table>"
    md = html_to_markdown(html)
    assert "| 名称 | 值 |" in md
    assert "| --- | --- |" in md
    assert "| A | 1 |" in md


def test_noise_tags_removed():
    html = "<article><nav>导航</nav><script>var x=1;</script><style>.a{}</style><p>正文</p><footer>页脚</footer></article>"
    md = html_to_markdown(html)
    assert "正文" in md
    assert "导航" not in md
    assert "var x=1" not in md
    assert "页脚" not in md


def test_nested_paragraphs_keep_blank_lines():
    html = "<p>第一段</p><p>第二段</p>"
    md = html_to_markdown(html)
    assert "第一段\n\n第二段" in md
