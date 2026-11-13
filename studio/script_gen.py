"""商品情報(item.json)から台本を作る。出品情報に書かれた事実だけを使う。

各シーン: kind(動作の型), voice(読み上げ文), caption(字幕), expr(表情)
"""

def _cm(v):
    return f"{v:g}"


def silhouette_word(m):
    w = m.get("ワタリ")
    if w is None:
        return None
    if w >= 34:
        return "極太"
    if w >= 30:
        return "太め"
    return "すっきり"


def build_script(item):
    brand_kana = item.get("brand_kana") or item.get("brand", "")
    brand = item.get("brand", brand_kana)
    color = item.get("color", "")
    material = item.get("material", "")
    cat = item.get("category", "古着")
    model = item.get("model", "")
    m = item.get("measurements_cm", {})
    cond = item.get("condition", "")
    notes = item.get("condition_notes", [])

    scenes = [dict(kind="hello", voice="どうも、古着くんです！", caption="どうも、古着くんです！", expr="笑顔")]

    # 冒頭フック:大きい数字があれば数字で、なければ問いかけ
    waist = m.get("ウエスト")
    hl = item.get("highlight")
    who = f"{color}の{brand_kana}" if color else f"この{brand_kana}"
    fit = item.get("fit")
    if hl:
        scenes.append(dict(kind="hook", voice=f"{who}、{hl}！？", caption=f"{who}、\n{hl}！？", expr="驚き"))
    elif waist and waist >= 100:
        scenes.append(dict(kind="hook", voice=f"{who}、ウエスト{_cm(waist)}センチ！？",
                           caption=f"{who}、\nウエスト{_cm(waist)}cm！？", expr="驚き"))
    elif fit:
        scenes.append(dict(kind="hook", voice=f"{who}、シルエット見て！", caption=f"{who}、\nシルエット見て！", expr="驚き"))
    else:
        scenes.append(dict(kind="hook", voice=f"{who}、見てほしい！", caption=f"{who}、\n見てほしい！", expr="驚き"))

    # 商品の正体
    mat = f"{material}地の" if material else ""
    if model:
        scenes.append(dict(kind="p1", voice=f"定番の、{mat}{cat}。",
                           caption=f"定番の{mat}\n{cat}{model}", expr="通常"))
    elif mat:
        scenes.append(dict(kind="p1", voice=f"{mat}、{cat}。",
                           caption=f"{mat}\n{cat}", expr="通常"))
    else:
        scenes.append(dict(kind="p1", voice=f"今回紹介するのは、{cat}！",
                           caption=f"今回紹介するのは\n{cat}", expr="通常"))

    # サイズ感・シルエット
    sw = fit or silhouette_word(m)
    if sw and "裾幅" in m:
        scenes.append(dict(kind="p2", voice=f"ワタリ{_cm(m['ワタリ'])}センチ、裾幅{_cm(m['裾幅'])}センチの、{sw}シルエット！",
                           caption=f"ワタリ{_cm(m['ワタリ'])}cm・裾幅{_cm(m['裾幅'])}cmの\n{sw}シルエット", expr="通常"))
    elif m:
        k, v = next(iter(m.items()))
        scenes.append(dict(kind="p2", voice=f"{k}は{_cm(v)}センチ。", caption=f"{k} {_cm(v)}cm", expr="通常"))

    # 一押し:説明文に色落ちがあれば色落ち、なければ素材
    if "色落ち" in notes:
        if material:
            scenes.append(dict(kind="push", voice=f"一押しは、{color}{material}に出た、いい色落ち！",
                               caption=f"一押しは、{color}{material}に\n出た色落ち！", expr="自信のある表情"))
        else:
            scenes.append(dict(kind="push", voice="一押しは、古着ならではの、いい色落ち！",
                               caption="一押しは、古着ならではの\nいい色落ち！", expr="自信のある表情"))
    else:
        mt = material or "生地"
        scenes.append(dict(kind="push", voice=f"一押しは、{mt}の、しっかりした質感！",
                           caption=f"一押しは\n{mt}の質感！", expr="自信のある表情"))

    # 締め:状態に傷や汚れがあれば正直に写真確認を促す
    if "目立つ" in cond:
        scenes.append(dict(kind="cta", voice="使用感はあるから、写真もチェックしてね！",
                           caption="使用感はあるので\n写真をチェック！", expr="笑顔"))
    elif "傷" in cond or "汚れ" in cond:
        scenes.append(dict(kind="cta", voice="細かい状態は、写真でチェックしてね！",
                           caption="細かい状態は\n写真でチェック！", expr="笑顔"))
    else:
        scenes.append(dict(kind="cta", voice="気になったら、プロフのリンクからチェックしてね！",
                           caption="気になったら\nプロフのリンクから！", expr="笑顔"))
    scenes.append(dict(kind="bye", voice="またね！", caption="またね！", expr="笑顔"))

    chips = {}
    chips["p1"] = " ".join(x for x in ["①", brand, model or hl or "", f"{material}地" if (material and not (hl and not model)) else ""] if x)
    if sw:
        chips["p2"] = f"② ワタリ{_cm(m['ワタリ'])}cmの{sw}"
    if "色落ち" in notes:
        chips["push"] = f"③ {color}の色落ち" if color else "③ いい色落ち"
    else:
        chips["push"] = f"③ {material}の生地感" if material else "③ 生地感"
    return scenes, chips
