"""TikTokのキャプションとXの投稿文を作る(事実だけを使い、毎回切り口を変える)。"""
import hashlib
from datetime import datetime
from script_gen import facts, _yen, _cm, SHOP_TEXT

CREDIT = "音声：VOICEVOX:白上虎太郎"


def x_len(s):
    """Xの文字数(全角は2、URLは23として数える)"""
    import re
    n = 0
    for part in re.split(r"(https?://\S+)", s):
        if part.startswith("http"):
            n += 23
        else:
            n += sum(2 if ord(c) > 0x10FF else 1 for c in part)
    return n


def hashtags(item, f, n=6):
    tags = ["古着", "古着男子", "古着コーデ"]
    b = item.get("brand", "")
    if b:
        tags.insert(0, b.replace(" ", ""))
    if f["brand"] and f["brand"] != b:
        tags.insert(1, f["brand"])
    if f["cat"]:
        tags.append(f["cat"].replace(" ", ""))
    if item.get("sale_type") == "auction":
        tags.append("メルカリオークション")
    tags.append("メルカリ")
    out = []
    for t in tags:
        if t and t not in out:
            out.append(t)
    return ["#" + t for t in out[:n]]


def make_posts(item, plan, variant=0):
    f = facts(item)
    url = item["url"]
    start = f["start"]
    sp = f"{_yen(start)}円スタート" if start else None
    m = f["m"]
    size = f"ワタリ{_cm(m['ワタリ'])}cm・裾幅{_cm(m['裾幅'])}cm" if ("ワタリ" in m and "裾幅" in m) else ""
    end = f["end"][1] if f["end"] else None
    tags = hashtags(item, f)

    hook = {
        "price": f"えっ、{f['brand']}が{sp}！？" if sp else f"{f['who']}、見てほしい！",
        "intro": "今日の一着はこれ！",
        "hype": "これ、アツい！",
        "rare": ("USA製の" if f["usa"] else "ヴィンテージの") + f"{f['brand']}！",
        "detail": "このディテール、見て！",
        "question": f"この{f['brand']}、いくらから始まると思う？",
        "auction": f"オークション、{end}まで！" if end else "オークション開催中！",
        "comedy": "ちょ、ちょっと待って…",
    }[plan["pattern"]]
    lines = [hook, f["label"]]
    if size:
        lines.append(size)
    if sp:
        lines.append(f"▶ {sp}")
    lines.append("気になったらプロフのリンクからチェック！")
    caption = "\n".join(lines) + "\n\n" + " ".join(tags) + "\n" + CREDIT

    # X:切り口を変えた候補を作り、商品ごと・回ごとに順番を変える
    cands = []
    if sp:
        cands.append(("価格", f"【{sp}】\n{f['label']}\nこの価格から狙えます。\n{url}"))
        cands.append(("お得", f"{f['brand']}を{_yen(start)}円から狙えるチャンス。\n{f['thing']}{('／' + size) if size else ''}\n{url}"))
    cands.append(("特徴", f"{f['label']}\n{size + '。' if size else ''}{'いい色落ちが出てます。' if '色落ち' in f['notes'] else ''}\n{url}"))
    if f["hl"] or f["usa"]:
        star = f["hl"] or "USA製"
        cands.append(("人気", f"{f['brand']}の{star}、出品しました。\n{f['thing']}{('／' + sp) if sp else ''}\n{url}"))
    if end:
        cands.append(("終了告知", f"⏰ {end}終了\n{f['label']}{('（' + sp + '）') if sp else ''}\n{url}"))
    h = int(hashlib.sha256(f"{item['item_id']}:{variant}".encode()).hexdigest(), 16)
    k = h % len(cands)
    cands = cands[k:] + cands[:k]
    xs = []
    for kind, txt in cands:
        txt = "\n".join(l for l in txt.split("\n") if l.strip())
        tag = " #古着 #" + (item.get("brand", "") or "古着コーデ").replace(" ", "")
        if x_len(txt + tag) <= 280:
            txt += tag
        if x_len(txt) <= 280:
            xs.append(dict(angle=kind, text=txt, length=x_len(txt)))
    return dict(item_id=item["item_id"], pattern=plan["pattern"], pattern_name=plan["pattern_name"],
                tiktok=dict(caption=caption, hashtags=tags), x=xs,
                facts=dict(start_price_yen=start, auction_end=item.get("auction_end"), url=url),
                generated_at=datetime.now().isoformat(timespec="seconds"))
