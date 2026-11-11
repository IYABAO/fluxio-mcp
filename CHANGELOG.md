# Changelog

## v0.2.0 — 2026-11-11

抓取健壮性专项：把"偶发失败"和"源本身不可用"分开，并让中文站不再整页乱码。

### 新增

- 分级超时：连接 5s、读取 15s，可用 `httpx.Timeout` 覆盖。
- 瞬时错误重试：429 / 500 / 502 / 503 / 504、连接/读写超时、连接中断，默认重试 2 次，指数退避。
- 确定性错误不重试：403 / 404 等直接抛 `httpx.HTTPStatusError`，避免把配额浪费在无效请求上。
- 流式体积上限：超过 `max_bytes`（默认 5MB）立即中止并抛 `ValueError`，不再先下载再判断。
- 编码回退：响应头 charset → UTF-8 → GB18030，最后才容错替换。
- RSS 解析失败诊断：新增 `RSSParseError` 与 `parse_rss(..., strict=True)`，区分「不是合法 XML」「拿到的是网页」「源可解析但无条目」。
- RSS 标题与摘要去 HTML、反转义、压平空白。

### 变更

- `fetch_rss` 的错误提示按失败类型分别返回，不再统一说"未解析到文章"。
- CI 只跑稳定单测（`pytest -m "not network"`）；真实网络用例改由本机 `pytest -m network` 执行，避免 runner 出网抖动造成假失败。
- 版本号 0.1.0 → 0.2.0。

### 测试

- 新增 8 个用例：5xx 重试成功、404 不重试、超限不重试、charset 解码、无 charset 走 GB18030、strict XML 报错、网页被识别、空源返回空、摘要去标签。
- 全量 33 passed（含 2 个真实网络用例）。

## v0.1.0

- RSS/Atom 解析、网页正文提取、网页转 Markdown、Bing/DuckDuckGo 搜索、多 URL 批量抓取、`rss://` 资源。
