"""メルカリWeb版の商品ページから商品情報と写真を取り込み、items/<ID>/ を作る。

方針: 自分の出品ページのみ / 1商品につきページ1回+写真 / ログインしない / 間隔を空ける
使い方: python studio/fetch_item.py <商品URLまたはID> [--probe]
"""
import sys, re, json, time, html, pathlib, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja-JP,ja;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        return (data if binary else data.decode("utf-8", "replace")), r.status


def item_id_from(s):
    m = re.search(r"(m\d{8,})", s)
    if not m:
        raise ValueError(f"商品IDが見つかりません: {s}")
    return m.group(1)


def meta(page, prop):
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop), page)
    if not m:
        m = re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="%s"' % re.escape(prop), page)
    return html.unescape(m.group(1)) if m else None


def json_ld(page):
    out = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            out.append(json.loads(m.group(1)))
        except Exception:
            pass
    return out


def probe(item_id):
    url = f"https://jp.mercari.com/item/{item_id}"
    page, st = get(url)
    print("status", st, "length", len(page))
    for p in ("og:title", "og:description", "og:image", "product:price:amount", "description"):
        v = meta(page, p)
        print(f"[meta {p}]", (v or "")[:300])
    lds = json_ld(page)
    print("json-ld count", len(lds))
    for ld in lds:
        print(json.dumps(ld, ensure_ascii=False)[:1500])
    print("__NEXT_DATA__" in page, "next data present")
    imgs = sorted(set(re.findall(r'https://static\.mercdn\.net/[^"\'\s?]+', page)))
    print("static images in html:", len(imgs), imgs[:12])
    for n in range(1, 4):
        u = f"https://static.mercdn.net/item/detail/orig/photos/{item_id}_{n}.jpg"
        try:
            b, s2 = get(u, binary=True); print("photo", n, s2, len(b))
        except urllib.error.HTTPError as e:
            print("photo", n, e.code)
        time.sleep(1)


if __name__ == "__main__":
    probe(item_id_from(sys.argv[1]))
