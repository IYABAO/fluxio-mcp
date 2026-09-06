"""fetch_urls 批量抓取测试。"""

import pytest

from fluxio_mcp.batch import fetch_urls


def test_fetch_urls_normalizes_and_limits():
    data = fetch_urls(["  https://example.com  ", "  ", "https://example.org", "https://a.com", "https://b.com", "https://c.com"], max_chars=500)
    # 空项剔除 + 最多 5 个
    assert len(data["results"]) == 5


def test_fetch_urls_bad_url_returns_error_entry():
    data = fetch_urls(["not-a-url"], max_chars=500)
    r = data["results"][0]
    assert r["ok"] is False
    assert r.get("error")


@pytest.mark.network
def test_fetch_urls_real():
    """真实网络：两个可用站点 + 一个无效站，验证单点失败不影响整体。"""
    data = fetch_urls(
        ["https://www.ruanyifeng.com/blog/", "https://this-domain-should-not-exist-xyz123.com/", "https://www.plbear.com/"],
        mode="markdown",
        max_chars=800,
    )
    results = data["results"]
    assert len(results) == 3
    ok_count = sum(1 for r in results if r["ok"])
    # 至少阮一峰和 plbear 成功
    assert ok_count >= 2
    assert any(r["ok"] is False for r in results)  # 无效站走错误分支
