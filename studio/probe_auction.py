import sys, asyncio, json
from playwright.async_api import async_playwright
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, o
async def main(item):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(user_agent=UA, locale="ja-JP", timezone_id="Asia/Tokyo")
        pg = await ctx.new_page()
        got = []
        async def on_resp(r):
            if "application/json" in (r.headers.get("content-type") or "") and item in r.url:
                try:
                    got.append((r.url, await r.json()))
                except Exception:
                    pass
        pg.on("response", on_resp)
        await pg.goto(f"https://jp.mercari.com/item/{item}", wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(2000)
        print("=====ITEM=====", item, len(got))
        for url, js in got:
            print("URL", url.split("?")[0])
            for path, v in walk(js):
                if any(k in path.lower() for k in ("auction", "bid", "price", "start", "end", "expire", "status", "num_", "count", "like", "comment")):
                    print("  ", path, "=", str(v)[:80])
        await b.close()
for it in sys.argv[1:]:
    asyncio.run(main(it))
