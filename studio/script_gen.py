"""商品情報(item.json)から台本を作る(v3:8つの演出パターン)。

ルール
- 出品情報・ページの商品データにある事実だけを使う。開始価格は auction_info.initial_price の値だけを使い、
  取れなかった場合は価格を言わない構成に切り替える(推測しない)
- 希少性は「USA製」「ヴィンテージ」などタイトルに書かれた事実がある時だけ
- 「ふるぎコムだけ」など、事実と異なる独占性は言わない

各シーン:
  gesture: hello/hook/point/explain/detail/push/price/hold/call/think/doubletake/bye
  voice / caption / expr / style(わーい・ふつう など) / speed / intonation / volume / pause(前の間)
  telop: big(画面上部に大きく) / sub(下の字幕) / price(価格ドーン)
  shot: 写真の見せ方 full / top / knee / hem / full2 / full3
  sfx: pop / whoosh / ding / drum / boing / shutter
"""
import hashlib
from datetime import datetime

SHOP_VOICE = "ふるぎコム"
SHOP_TEXT = "古着コム"
PATTERNS = ["price", "intro", "hype", "rare", "detail", "question", "auction", "comedy"]
PATTERN_NAMES = {"price": "価格訴求型", "intro": "商品紹介型", "hype": "テンション型", "rare": "希少性訴求型",
                 "detail": "ディテール型", "question": "問いかけ型", "auction": "オークション訴求型", "comedy": "コメディ型"}


def _cm(v):
    return f"{v:g}"


def _yen(v):
    return f"{int(v):,}"


def silhouette_word(m):
    w = m.get("ワタリ")
    if w is None:
        return None
    return "極太" if w >= 34 else ("太め" if w >= 30 else "すっきり")


def facts(item):
    m = item.get("measurements_cm", {})
    title = item.get("title", "")
    f = dict(
        brand=item.get("brand_kana") or item.get("brand") or "この古着",
        color=item.get("color", ""), material=item.get("material", ""),
        cat=item.get("category") or "古着", model=item.get("model", ""),
        hl=item.get("highlight", ""), fit=item.get("fit") or silhouette_word(m) or "",
        m=m, notes=item.get("condition_notes", []), cond=item.get("condition", ""),
        start=item.get("start_price_yen") if item.get("sale_type") == "auction" else None,
        fixed=item.get("price_yen") if item.get("sale_type") == "fixed" else None,
        usa="USA製" in title or "アメリカ製" in title,
        vintage=any(w in title for w in ("ヴィンテージ", "ビンテージ", "vintage", "VINTAGE", "90s", "80s")),
        end=None,
    )
    if item.get("auction_end") and item.get("status") == "on_sale":
        try:
            e = datetime.fromisoformat(item["auction_end"])
            f["end"] = (e, f"{e.month}月{e.day}日の{e.hour}時{e.minute:02d}分" if e.minute else f"{e.month}月{e.day}日の{e.hour}時")
        except Exception:
            pass
    f["who"] = f"{f['color']}の{f['brand']}" if f["color"] else f"この{f['brand']}"
    f["thing"] = f"{f['material']}地の{f['cat']}" if f["material"] else f["cat"]
    f["spoken"] = f"{f['color']}の{f['brand']}、{f['thing']}" if f["color"] else f"{f['brand']}の、{f['thing']}"
    f["label"] = f"{f['brand']} {f['thing']}" + (f"（{f['color']}）" if f["color"] else "")
    return f


def S(gesture, voice, caption=None, expr="通常", style="ふつう", speed=1.1, intonation=1.25, volume=1.0,
      pause=0.18, telop="sub", shot="full", sfx=None):
    return dict(gesture=gesture, kind=gesture, voice=voice, caption=caption or voice, expr=expr, style=style,
                speed=speed, intonation=intonation, volume=volume, pause=pause, telop=telop, shot=shot, sfx=sfx)


def size_scene(f, shot="full2"):
    m = f["m"]
    if "ワタリ" in m and "裾幅" in m:
        fit = f["fit"] or "程よい"
        return S("explain", f"ワタリ{_cm(m['ワタリ'])}センチ、裾幅{_cm(m['裾幅'])}センチの、{fit}シルエット。",
                 f"ワタリ{_cm(m['ワタリ'])}cm・裾幅{_cm(m['裾幅'])}cm\n{fit}シルエット", speed=1.08, intonation=1.1, shot=shot)
    if "着丈" in m and "身幅" in m:
        return S("explain", f"着丈{_cm(m['着丈'])}センチ、身幅{_cm(m['身幅'])}センチ。",
                 f"着丈{_cm(m['着丈'])}cm・身幅{_cm(m['身幅'])}cm", speed=1.08, intonation=1.1, shot=shot)
    if m:
        k, v = next(iter(m.items()))
        return S("explain", f"{k}は{_cm(v)}センチ。", f"{k} {_cm(v)}cm", shot=shot)
    return None


def fade_scene(f, gesture="push", shot="knee"):
    sfx = "ding" if gesture == "push" else "shutter"
    if "色落ち" in f["notes"] or "フェード" in f["notes"]:
        base = f"{f['color']}{f['material']}" if (f["color"] or f["material"]) else "古着ならでは"
        return S(gesture, f"一押しは、{base}の、いい色落ち！", f"一押しは\n{base}の色落ち！",
                 expr="自信のある表情", intonation=1.35, shot=shot, sfx=sfx)
    mt = f["material"] or "生地"
    return S(gesture, f"一押しは、{mt}の、しっかりした質感！", f"一押しは\n{mt}の質感！",
             expr="自信のある表情", intonation=1.35, shot=shot, sfx=sfx)


def condition_scene(f):
    c = f["cond"]
    if c.startswith("傷や汚れあり") or c == "全体的に状態が悪い" or "目立つ" in c:
        return S("call", "使用感はあるから、写真もチェックしてね！", "使用感あり\n写真をチェック！", expr="笑顔", pause=0.25)
    if "傷" in c or "汚れ" in c:
        return S("call", "細かい状態は、写真でチェックしてね！", "細かい状態は\n写真でチェック！", expr="笑顔", pause=0.25)
    return None


def price_scene(f, voice=None, caption=None, style="わーい"):
    if f["start"]:
        return S("price", voice or f"なんと、{_yen(f['start'])}円スタート！", caption or f"¥{_yen(f['start'])}スタート！",
                 expr="驚き", style=style, speed=1.0, intonation=1.55, volume=1.15, pause=0.45, telop="price", shot="full", sfx="drum")
    if f["fixed"]:
        return S("price", f"お値段は、{_yen(f['fixed'])}円！", f"¥{_yen(f['fixed'])}", expr="自信のある表情", style=style,
                 speed=1.0, intonation=1.45, volume=1.1, pause=0.4, telop="price", shot="full", sfx="drum")
    return None


def cta_scene(f, voice=None):
    return S("call", voice or "気になったら、プロフのリンクからチェックしてね！", "プロフのリンクから\nチェック！",
             expr="笑顔", intonation=1.3, pause=0.25)


def bye():
    return S("bye", "またね！", "またね！", expr="笑顔", style="わーい", speed=1.05, pause=0.2)


def p_price(f):
    if not f["start"]:
        return None
    return [S("hook", f"えっ、{f['brand']}が、{_yen(f['start'])}円スタート！？", f"{f['brand']}が\n{_yen(f['start'])}円スタート！？",
              expr="驚き", style="わーい", speed=1.05, intonation=1.6, volume=1.15, telop="big", sfx="pop"),
            S("point", f"{f['spoken']}。", f"{f['brand']}\n{f['thing']}", shot="full2", sfx="whoosh"),
            size_scene(f, "full3"), fade_scene(f, "detail", "knee"),
            price_scene(f, "この価格から狙えるチャンス、見逃せない！", f"¥{_yen(f['start'])}から\n狙える！"),
            cta_scene(f, f"{f['brand']}をお得に狙うなら、{SHOP_VOICE}！プロフのリンクからチェック！"), bye()]


def p_intro(f):
    return [S("hello", "どうも、古着くんです！今日の一着はこれ！", "今日の一着はこれ！", expr="笑顔", style="わーい", telop="big", sfx="pop"),
            S("point", f"{f['spoken']}。", f"{f['brand']}\n{f['thing']}", shot="full", sfx="whoosh"),
            size_scene(f, "full2"), fade_scene(f, "push", "knee"),
            price_scene(f, f"スタートは、{_yen(f['start'])}円から。" if f["start"] else None, style="ふつう"),
            condition_scene(f), cta_scene(f), bye()]


def p_hype(f):
    star = f["hl"] or f["thing"]
    return [S("hook", "うわっ、これ、アツい！", "これ、アツい！", expr="驚き", style="わーい", speed=1.15, intonation=1.7, volume=1.2, telop="big", sfx="pop"),
            S("point", f"{f['brand']}の、{star}！", f"{f['brand']}の\n{star}！", expr="自信のある表情", style="わーい", speed=1.12, intonation=1.5, sfx="whoosh"),
            fade_scene(f, "push", "knee"),
            price_scene(f, f"しかも、{_yen(f['start'])}円スタート！" if f["start"] else None),
            S("call", "気になったら、今すぐチェック！", "今すぐチェック！", expr="笑顔", style="わーい", intonation=1.5), bye()]


def p_rare(f):
    if not (f["usa"] or f["vintage"]):
        return None
    tag = "USA製" if f["usa"] else "ヴィンテージ"
    return [S("hook", f"{tag}の、{f['brand']}！", f"{tag}の\n{f['brand']}！", expr="驚き", style="わーい", intonation=1.55, telop="big", sfx="pop"),
            S("hold", f"{f['thing']}。古着ならではの一本。", f"{f['thing']}\n古着ならではの一本", shot="full2", sfx="whoosh"),
            S("detail", "タグまわりも、チェックしてみて。", "タグまわりも\nチェック", shot="top", sfx="shutter"),
            size_scene(f, "full3"), price_scene(f), condition_scene(f), cta_scene(f), bye()]


def p_detail(f):
    return [S("hook", "このディテール、見て！", "このディテール\n見て！", expr="驚き", style="わーい", telop="big", sfx="pop"),
            S("detail", f"まずは、{f['brand']}らしい、ウエストまわり。", f"{f['brand']}らしい\nウエストまわり", shot="top", sfx="shutter"),
            fade_scene(f, "detail", "knee"),
            S("detail", "裾の雰囲気も、いい感じ。", "裾の雰囲気も\nいい感じ", shot="hem", sfx="shutter"),
            size_scene(f, "full"), price_scene(f, f"これで、{_yen(f['start'])}円スタート！" if f["start"] else None),
            cta_scene(f), bye()]


def p_question(f):
    if not f["start"]:
        return None
    return [S("think", f"この{f['brand']}、いくらから始まると思う？", f"この{f['brand']}\nいくらから？", expr="困り顔", intonation=1.4, telop="big", sfx="pop"),
            S("point", f"{f['spoken']}。", f"{f['brand']}\n{f['thing']}", shot="full2", sfx="whoosh"),
            size_scene(f, "full3"),
            price_scene(f, f"正解は、{_yen(f['start'])}円スタート！", f"正解は\n¥{_yen(f['start'])}スタート！"),
            S("call", "当たった人は、コメントで教えて！", "当たったら\nコメントで！", expr="笑顔", style="わーい", intonation=1.4),
            cta_scene(f), bye()]


def p_auction(f):
    if not (f["start"] and f["end"]):
        return None
    return [S("hook", f"オークション、{f['end'][1]}まで！", f"オークション\n{f['end'][1]}まで！", expr="驚き", style="わーい", telop="big", sfx="pop"),
            S("point", f"{f['spoken']}。", f"{f['brand']}\n{f['thing']}", shot="full2", sfx="whoosh"),
            fade_scene(f, "push", "knee"),
            price_scene(f, f"{_yen(f['start'])}円スタートで、参加できる！", f"¥{_yen(f['start'])}スタート\n参加できる！"),
            cta_scene(f, "終わる前に、プロフのリンクからチェックしてね！"), bye()]


def p_comedy(f):
    if not f["start"]:
        return None
    return [S("doubletake", "ちょ、ちょっと待って…", "ちょ、ちょっと待って…", expr="困り顔", style="びくびく", speed=0.95, intonation=1.3, telop="big", sfx="boing"),
            S("hook", f"この{f['brand']}、{_yen(f['start'])}円スタートって、ほんと！？", f"{f['brand']}が\n{_yen(f['start'])}円スタート！？",
              expr="驚き", style="わーい", intonation=1.65, volume=1.2, telop="big", sfx="pop"),
            S("point", f"{f['thing']}だよ？", f"{f['thing']}だよ？", shot="full2", sfx="whoosh"),
            fade_scene(f, "push", "knee"),
            S("call", "古着くん、思わず二度見しちゃった！", "思わず二度見！", expr="笑顔", style="わーい", sfx="boing"),
            cta_scene(f), bye()]


BUILDERS = {"price": p_price, "intro": p_intro, "hype": p_hype, "rare": p_rare, "detail": p_detail,
            "question": p_question, "auction": p_auction, "comedy": p_comedy}


def rank_patterns(item):
    f = facts(item)
    score = {p: 0.0 for p in PATTERNS}
    if f["start"] and f["start"] <= 3000:
        score["price"] += 3; score["question"] += 2; score["comedy"] += 1.5
    elif f["start"]:
        score["intro"] += 1; score["auction"] += 1
    if f["end"]:
        score["auction"] += 1.5
    if f["usa"] or f["vintage"]:
        score["rare"] += 2.5
    if f["hl"]:
        score["hype"] += 2
    if "色落ち" in f["notes"]:
        score["detail"] += 1.5
    score["intro"] += 1
    try:   # 過去の成果(analyze)で伸びたパターンを少し優先する
        import json, pathlib
        w = json.loads((pathlib.Path(__file__).resolve().parent.parent / "outputs" / "pattern_scores.json").read_text()).get("weights", {})
        for p, v in w.items():
            if p in score:
                score[p] += float(v)
    except Exception:
        pass
    h = int(hashlib.sha256(item["item_id"].encode()).hexdigest(), 16)
    for i, p in enumerate(PATTERNS):   # 同点のときに商品ごとに散らす
        score[p] += ((h >> (i * 4)) % 16) / 100
    ok = [p for p in sorted(PATTERNS, key=lambda p: -score[p]) if BUILDERS[p](f) is not None]
    return ok, f


def build_script(item, variant=0, pattern=None, avoid=None):
    ranked, f = rank_patterns(item)
    if pattern and pattern in ranked:
        chosen = pattern
    else:
        pool = [p for p in ranked if p not in (avoid or [])] or ranked
        chosen = pool[variant % len(pool)]
    scenes = [s for s in BUILDERS[chosen](f) if s]
    chips = {"c1": " ".join(x for x in ["①", item.get("brand", ""), f["model"] or f["hl"],
                                         f"{f['material']}地" if f["material"] and not f["hl"] else ""] if x)}
    if "ワタリ" in f["m"]:
        chips["c2"] = f"② ワタリ{_cm(f['m']['ワタリ'])}cm{('の' + f['fit']) if f['fit'] else ''}"
    elif f["m"]:
        k, v = next(iter(f["m"].items())); chips["c2"] = f"② {k}{_cm(v)}cm"
    chips["c3"] = (f"③ {f['color']}の色落ち" if f["color"] else "③ いい色落ち") if "色落ち" in f["notes"] else f"③ {f['material'] or '生地'}の質感"
    return dict(pattern=chosen, pattern_name=PATTERN_NAMES[chosen], ranked=ranked), scenes, chips
