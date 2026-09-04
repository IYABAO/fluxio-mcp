"""真实 MCP stdio 握手验证：用 fastmcp Client 连接 fluxio-mcp，列出工具并调用。"""
import asyncio
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def main() -> None:
    transport = StdioTransport(
        sys.executable, ["-m", "fluxio_mcp"], cwd=r"E:\github\fluxio-mcp"
    )

    def text_of(res) -> str:
        return "".join(b.text for b in res.content if hasattr(b, "text"))

    async with Client(transport) as client:
        tools = await client.list_tools()
        names = [t.name for t in tools]
        print("CONNECTED. tools:", names)
        assert "fetch_rss" in names and "fetch_web" in names, "工具未注册齐全"

        res = await client.call_tool(
            "fetch_rss", {"url": "https://www.ruanyifeng.com/blog/atom.xml", "limit": 1}
        )
        print("fetch_rss ->", text_of(res)[:120].replace("\n", " "))

        res2 = await client.call_tool(
            "fetch_web", {"url": "https://www.plbear.com/", "max_chars": 200}
        )
        print("fetch_web ->", text_of(res2)[:120].replace("\n", " "))

        resources = await client.list_resources()
        print("resources:", [r.uri for r in resources])
    print("MCP 握手与工具调用全部通过 ✅")


if __name__ == "__main__":
    asyncio.run(main())
