"""メルカリWeb版の商品ページを開いて、商品情報と写真を items/<ID>/ に取り込む。

方針: 自分の出品のみ / 1商品につきページ表示1回+写真数枚 / ログインしない / 間隔を空ける
使い方:
  python studio/fetch_item.py <商品URLまたはID>             … 1商品を取り込む
  python studio/fetch_item.py --seller [出品者URL]          … 出品中の新しい商品をまとめて取り込む(最大5件)
"""
import sys, re, json, time, asyncio, pathlib, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
MAX_PHOTOS = 4
JST = timezone(timedelta(hours=9))

BRAND_KANA = {
    "carhartt": "カーハート", "levi's": "リーバイス", "levis": "リーバイス", "wrangler": "ラングラー",
    "dickies": "ディッキーズ", "ralph lauren": "ラルフローレン", "patagonia": "パタゴニア",
    "the north face": "ノースフェイス", "nike": "ナイキ", "adidas": "アディダス", "champion": "チャンピオン",
    "l.l.bean": "エルエルビーン", "eddie bauer": "エディーバウアー", "columbia": "コロンビア",
    "stussy": "ステューシー", "supreme": "シュプリーム", "harley-davidson": "ハーレーダビッドソン",
    "gap": "ギャップ", "hanes": "ヘインズ", "red kap": "レッドキャップ", "redkap": "レッドキャップ",
    "ben davis": "ベンデイビス", "schott": "ショット", "pendleton": "ペンドルトン", "lee": "リー",
}
COLORS = [("ハミルトンブラウン", "ブラウン"), ("ダックブラウン", "ブラウン"), ("ブラック", "黒"), ("黒", "黒"),
          ("ホワイト", "白"), ("モス", "モス"), ("ブラウン", "ブラウン"), ("ネイビー", "ネイビー"), ("グレー", "グレー"),
          ("カーキ", "カーキ"), ("ベージュ", "ベージュ"), ("オリーブ", "オリーブ"), ("グリーン", "グリーン"),
          ("レッド", "赤"), ("インディゴ", "インディゴ"), ("ブルー", "ブルー"), ("タン", "タン"),
          ("BLACK", "黒"), ("MOSS", "モス"), ("MOS", "モス"), ("BROWN", "ブラウン"), ("NAVY", "ネイビー"),
          ("GRAY", "グレー"), ("GREY", "グレー"), ("KHAKI", "カーキ"), ("OLIVE", "オリーブ"), ("WHITE", "白")]
MATERIALS = ["ダック", "デニム", "コーデュロイ", "スウェット", "ナイロン", "フリース", "レザー", "ツイル", "キャンバス", "ウール", "ネル"]
HIGHLIGHTS = ["ダブルニー", "デトロイト", "アクティブジャケット", "チョアコート", "サンタフェ", "リメイク"]
MEASURE_KEYS = ["着丈", "身幅", "肩幅", "袖丈", "ウエスト", "股上", "股下", "ワタリ", "わたり", "裾幅", "総丈"]


def item_id_from(s):
    m = re.search(r"(m\d{8,})", s)
    if not m:
        raise ValueError(f"商品IDが見つかりません: {s}")
    return m.group(1)


async def _page(p):
    b = await p.chromium.launch()
    pg = await b.new_page(user_agent=UA, locale="ja-JP", viewport={"width": 430, "height": 932})
    return b, pg


async def render(url):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b, pg = await _page(p)
        api = {}

        async def on_resp(r):
            if "/items/get" in r.url:
                try:
                    api.update((await r.json()).get("data") or {})
                except Exception:
                    pass
        pg.on("response", on_resp)
        await pg.goto(url, wait_until="networkidle", timeout=60000)
        await pg.wait_for_timeout(1500)

        async def text(sel):
            el = await pg.query_selector(sel)
            return (await el.inner_text()).strip() if el else ""
        seller = ""
        el = await pg.query_selector('a[href*="/user/profile/"]')
        if el:
            seller = await el.evaluate("e => e.href")
        data = {
            "name": await text('[data-testid="name"]'),
            "price": await text('[data-testid="price"]'),
            "description": await text('[data-testid="description"]'),
            "condition": await text('[data-testid="商品の状態"]'),
            "size": await text('[data-testid="サイズ"]'),
            "brand": await text('[data-testid="ブランド"]'),
            "category": await text('[data-testid="item-detail-category"]'),
            "checkout": await text('[data-testid="checkout-button-container"]'),
            "bid": bool(await pg.query_selector('[data-testid="bid-history-button"]')),
            "photos": len(await pg.query_selector_all('[data-testid^="image-"]')),
            "seller": seller,
            "api": api,
        }
        await b.close()
        return data


async def seller_items(url):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b, pg = await _page(p)
        await pg.goto(url, wait_until="networkidle", timeout=60000)
        for _ in range(3):
            await pg.mouse.wheel(0, 4000)
            await pg.wait_for_timeout(1200)
        links = await pg.eval_on_selector_all('a[href*="/item/m"]', "els => els.map(e => e.href)")
        await b.close()
    return list(dict.fromkeys(item_id_from(h) for h in links))


def clean_value(v, label):
    return re.sub(r"\s+", " ", v.replace(label, "")).strip()


CONDITIONS = ["新品、未使用", "未使用に近い", "目立った傷や汚れなし", "やや傷や汚れあり", "傷や汚れあり", "全体的に状態が悪い"]


def first_condition(v):
    return next((c for c in CONDITIONS if v.startswith(c)), v.split(" ")[0])


def num(s):
    return float(s) if "." in s else int(s)


def parse(item_id, d):
    name = re.sub(r"^\S*様\s*", "", d["name"]).strip()        # 「〇〇様」専用出品の接頭辞を外す
    desc = d["description"]
    text_all = f"{name}\n{desc}"
    price = int(re.sub(r"[^\d]", "", d["price"]) or 0)
    brand = clean_value(d["brand"], "ブランド")
    low = (brand + " " + name).lower()
    brand_kana = next((v for k, v in BRAND_KANA.items() if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", low)), brand)
    def find_color(t):
        for k, v in COLORS:
            if (re.search(r"(?<![A-Za-z])" + k + r"(?![A-Za-z])", t) if k.isascii() else k in t):
                return v
        return None
    color = find_color(name) or find_color(desc) or ""
    material = next((m for m in MATERIALS if m in name), "")   # 説明文の定型文に引っ張られないよう、タイトルからだけ取る
    highlight = next((h for h in HIGHLIGHTS if h in text_all), "")
    mm = re.search(r"(?<![A-Za-z0-9])([A-Z]{1,2}\d{2,3})(?![A-Za-z0-9])", name)
    model = mm.group(1) if mm else ""
    meas = {}
    for k in MEASURE_KEYS:
        m = re.search(k + r"\s*[:：]?\s*約?\s*(\d+(?:\.\d+)?)\s*(?:cm|ｃｍ|センチ)", desc)
        if m:
            meas["ワタリ" if k == "わたり" else k] = num(m.group(1))
    fit = "ワイド" if re.search(r"ワイド|リラックス|バギー|ルーズ", text_all) else ("極太" if "極太" in text_all else "")
    notes = [w for w in ("色落ち", "擦れ", "フェード", "ほつれ", "穴", "シミ", "汚れ") if w in desc]
    cat = clean_value(d["category"], "カテゴリー")
    cat = re.split(r"[>\n/]", cat)[-1].strip() if cat else ""
    if "・" in cat:   # 「ワークパンツ・カーゴパンツ・ペインターパンツ」→ 名前に含まれるものを優先
        parts = cat.split("・")
        cat = next((x for x in parts if x in name), parts[-1])
    if highlight and highlight not in cat and "パンツ" in cat:
        cat = f"{highlight}{cat}"
    return {
        "item_id": item_id,
        "url": f"https://jp.mercari.com/item/{item_id}",
        "title": name,
        "brand": brand, "brand_kana": brand_kana, "model": model,
        "category": cat or "古着",
        "highlight": "" if model else highlight,
        "material": material, "color": color, "fit": fit,
        "size_label": clean_value(d["size"], "サイズ"),
        "measurements_cm": meas,
        "condition": first_condition(clean_value(d["condition"], "商品の状態")),
        "condition_notes": notes,
        "price_yen": price,
        **auction_fields(d),
        "bgm": "auto",
        "description_raw": desc,
        "fetched_at": datetime.now(JST).isoformat(timespec="seconds"),
    }


def auction_fields(d):
    """開始価格などは、ページが受け取る商品データの値をそのまま使う(推測しない)"""
    api = d.get("api") or {}
    a = api.get("auction_info") or {}
    out = {}
    status = api.get("status")
    out["status"] = "sold" if status in ("sold_out", "trading", "sold") or "売り切れ" in d["checkout"] else "on_sale"
    out["api_status"] = status or ""
    out["num_likes"] = api.get("num_likes")
    out["num_comments"] = api.get("num_comments")
    if a:
        out["sale_type"] = "auction"
        out["start_price_yen"] = a.get("initial_price")
        out["highest_bid_yen"] = a.get("highest_bid")
        out["total_bids"] = a.get("total_bids")
        out["auction_state"] = a.get("state")
        end = a.get("expected_end_time")
        out["auction_end"] = datetime.fromtimestamp(int(end), JST).isoformat(timespec="minutes") if end else None
        if a.get("state") and a["state"] != "STATE_ONGOING" and out["status"] == "on_sale":
            out["status"] = "ended"
    else:
        out["sale_type"] = "auction" if (d["bid"] or "入札" in d["checkout"]) else "fixed"
        if out["sale_type"] == "auction":
            out["start_price_yen"] = None   # 取得できなかった(推測しない)
    return out


def download_photos(item_id, n, dest):
    dest.mkdir(parents=True, exist_ok=True)
    got = 0
    for i in range(1, min(max(n, 1), MAX_PHOTOS) + 1):
        url = f"https://static.mercdn.net/item/detail/orig/photos/{item_id}_{i}.jpg"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                (dest / f"{i:02d}.jpg").write_bytes(r.read())
                got += 1
        except Exception as e:
            print("写真の取得に失敗", i, e)
        time.sleep(1.0)
    return got


def import_item(src):
    item_id = item_id_from(src)
    d = asyncio.run(render(f"https://jp.mercari.com/item/{item_id}"))
    if not d["name"]:
        raise RuntimeError("商品ページを読み取れませんでした(削除済み・非公開の可能性)")
    item = parse(item_id, d)
    folder = ROOT / "items" / item_id
    path = folder / "item.json"
    if path.exists():   # 手で直した項目(manual_override)は上書きしない
        prev = json.loads(path.read_text())
        for k in prev.get("manual_override", []):
            item[k] = prev.get(k)
        item["manual_override"] = prev.get("manual_override", [])
    folder.mkdir(parents=True, exist_ok=True)
    if not any((folder / "photos").glob("*.jpg")):
        print("写真", download_photos(item_id, d["photos"], folder / "photos"), "枚")
    path.write_text(json.dumps(item, ensure_ascii=False, indent=2))
    log = ROOT / "metrics" / "mercari" / f"{item_id}.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps({k: item.get(k) for k in ("fetched_at", "status", "price_yen", "start_price_yen", "highest_bid_yen",
                                                      "total_bids", "num_likes", "num_comments", "auction_end")}, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in item.items() if k != "description_raw"}, ensure_ascii=False, indent=1))
    if d.get("seller"):
        (ROOT / "items" / ".seller").write_text(d["seller"])
    return item


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--refresh" in sys.argv:   # 販売中の商品の価格・入札・いいねを1日1回更新(古い順に最大N件)
        n = int(args[0]) if args else 8
        cands = []
        for pth in (ROOT / "items").glob("m*/item.json"):
            it = json.loads(pth.read_text())
            stale = it.get("fetched_at", "") < (datetime.now(JST) - timedelta(hours=20)).isoformat()
            missing = "api_status" not in it   # 開始価格などを未確認の(古い形式の)商品は優先して取り直す
            if it.get("status") == "on_sale" and (stale or missing):
                cands.append(("0" if missing else it.get("fetched_at", ""), it["item_id"]))
        for _, i in sorted(cands)[:n]:
            try:
                import_item(i)
            except Exception as e:
                print("更新失敗", i, e)
            time.sleep(3)
        sys.exit(0)
    if "--seller" in sys.argv:
        f = ROOT / "items" / ".seller"
        url = args[0] if args else (f.read_text().strip() if f.exists() else "")
        if not url:
            sys.exit("出品者ページが未登録です。先に商品URLを1つ取り込んでください。")
        if not url.startswith("http"):
            url = f"https://jp.mercari.com/user/profile/{url}"
        ids = asyncio.run(seller_items(url))
        new = [i for i in ids if not (ROOT / "items" / i / "item.json").exists()]
        print("出品者ページの商品", len(ids), "件 / 新規", new)
        for i in new[:5]:
            try:
                import_item(i)
            except Exception as e:
                print("取り込み失敗", i, e)
            time.sleep(3)
    else:
        for a in args:
            import_item(a)
