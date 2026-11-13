import sys, asyncio, re
from playwright.async_api import async_playwright
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
async def main(item):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(user_agent=UA, locale="ja-JP", viewport={"width": 430, "height": 932})
        await pg.goto(f"https://jp.mercari.com/item/{item}", wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(1500)
        body = await pg.inner_text("body")
        print("=====ITEM=====", item)
        for kw in ("開始", "入札", "終了", "残り", "現在", "即決", "オークション"):
            for m in list(re.finditer(kw, body))[:3]:
                print(f"[{kw}]", body[max(0, m.start()-60):m.start()+80].replace("\n", " | "))
        ids = await pg.eval_on_selector_all("[data-testid]", "els => [...new Set(els.map(e => e.getAttribute('data-testid')))]")
        print("TESTIDS", [x for x in ids if any(k in x for k in ("auction","bid","price","time","checkout","countdown"))])
        for sel in ('[data-testid="checkout-button-container"]', '[data-testid="price"]'):
            el = await pg.query_selector(sel)
            print(sel, (await el.inner_text()).replace("\n"," | ") if el else None)
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
