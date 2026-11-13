import sys, asyncio, re
from playwright.async_api import async_playwright
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
async def main(item):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(user_agent=UA, locale="ja-JP", viewport={"width": 430, "height": 932})
        await pg.goto(f"https://jp.mercari.com/item/{item}", wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(1500)
        c = await pg.query_selector('[data-testid="item-detail-container"]')
        t = await c.inner_text() if c else ""
        print("=====DETAIL=====", item); print(t[:2500])
        bh = await pg.query_selector('[data-testid="bid-history-button"]')
        if bh:
            print("=====BIDBTN=====", await bh.inner_text())
            await bh.click(); await pg.wait_for_timeout(2500)
            body = await pg.inner_text("body")
            i = body.find("入札")
            print("=====BIDHIST=====", body[max(0,i-200):i+1500])
        await b.close()
for it in sys.argv[1:]:
    asyncio.run(main(it))
