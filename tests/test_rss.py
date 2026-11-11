import pytest

from fluxio_mcp.rss import RSSParseError, parse_rss

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>测试源</title>
  <item>
    <title>第一篇</title>
    <link>https://example.com/1</link>
    <pubDate>Wed, 02 Oct 2024 08:00:00 GMT</pubDate>
    <description>第一篇摘要</description>
  </item>
  <item>
    <title>第二篇</title>
    <link>https://example.com/2</link>
    <pubDate>Thu, 03 Oct 2024 08:00:00 GMT</pubDate>
    <description>第二篇摘要</description>
  </item>
  <item>
    <title>无链接</title>
    <description>跳过此条</description>
  </item>
</channel></rss>
"""

ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom 源</title>
  <entry>
    <title>Atom 文章</title>
    <link href="https://atom.example.com/1" rel="alternate"/>
    <published>2024-10-04T09:30:00Z</published>
    <summary>Atom 摘要</summary>
  </entry>
</feed>
"""


def test_parse_rss_items():
    articles = parse_rss(RSS_XML)
    assert len(articles) == 2
    assert articles[0].title == "第一篇"
    assert articles[0].link == "https://example.com/1"
    assert articles[0].pub_date == "Wed, 02 Oct 2024 08:00:00 GMT"
    assert articles[0].summary == "第一篇摘要"


def test_parse_atom_entries():
    articles = parse_rss(ATOM_XML)
    assert len(articles) == 1
    assert articles[0].title == "Atom 文章"
    assert articles[0].link == "https://atom.example.com/1"
    assert articles[0].pub_date == "2024-10-04T09:30:00Z"
    assert articles[0].summary == "Atom 摘要"


def test_parse_limit():
    articles = parse_rss(RSS_XML, limit=1)
    assert len(articles) == 1


def test_parse_invalid_returns_empty():
    assert parse_rss("<not-xml>") == []
    assert parse_rss("") == []


def test_strict_invalid_xml_raises_with_reason():
    with pytest.raises(RSSParseError, match="XML 解析失败"):
        parse_rss("<not-xml>", strict=True)


def test_strict_html_page_is_rejected():
    page = "<!DOCTYPE html><html><head><title>首页</title></head><body>hi</body></html>"
    with pytest.raises(RSSParseError, match="网页"):
        parse_rss(page, strict=True)


def test_strict_empty_feed_returns_empty_list():
    empty_feed = '<?xml version="1.0"?><rss version="2.0"><channel><title>空源</title></channel></rss>'
    assert parse_rss(empty_feed, strict=True) == []


def test_summary_html_is_stripped():
    feed = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item>
        <title>带标签的摘要</title>
        <link>https://example.com/tagged</link>
        <description><![CDATA[<p>摘要&nbsp;<b>内容</b></p>]]></description>
      </item>
    </channel></rss>"""
    articles = parse_rss(feed)
    assert articles[0].summary == "摘要 内容"
    assert "<p>" not in articles[0].summary


def test_utf8_bom_feed_parses():
    assert len(parse_rss("\ufeff" + RSS_XML)) == 2
