import sys, asyncio
from playwright.async_api import async_playwright
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
async def main(item):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(user_agent=UA, locale="ja-JP", viewport={"width": 430, "height": 932})
        await pg.goto(f"https://jp.mercari.com/item/{item}", wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(2000)
        txt = await pg.inner_text("main") if await pg.query_selector("main") else await pg.inner_text("body")
        print("=====TEXT=====")
        print(txt[:6000])
        ids = await pg.eval_on_selector_all("[data-testid]", "els => [...new Set(els.map(e => e.getAttribute('data-testid')))]")
        print("=====TESTIDS=====", ids[:80])
        await b.close()
asyncio.run(main(sys.argv[1]))
