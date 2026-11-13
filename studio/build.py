"""古着くん 商品紹介ショート動画を作る(v3)。

使い方: python studio/build.py <item_id> [--variant N] [--pattern 名前] [--mock-tts]
        python studio/build.py --pending / --list-pending
入力:  items/<item_id>/item.json, items/<item_id>/photos/*.jpg
出力:  outputs/<item_id>/furugikun_<item_id>.mp4, voice.wav, script.json, posts.json, post.txt
"""
import sys, os, json, math, wave, array, base64, glob, hashlib, subprocess, pathlib, shutil
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import views as V, rig, tts, bgm, sfx
from script_gen import build_script
import posts

W, H, FPS = 1080, 1920, 30
INK = '#2A1E18'; FONT = 'Noto Sans CJK JP'
TAIL = 0.8
CREDIT = 'VOICEVOX:白上虎太郎'
CHAR_X, CHAR_Y = 640, 1075   # 古着くんの立ち位置


def P(*ds, **kw):
    out = {}
    for d in ds:
        out.update(d)
    out.update(kw)
    return out


# ---------- ポーズ ----------
REST_L = dict(L_up=8, L_fore=0, L_hand=0, L_pose='rest')
REST_R = dict(R_up=8, R_fore=0, R_hand=0, R_pose='rest')
WAVE_R = dict(R_up=150, R_fore=22, R_hand=0, R_pose='open')
SURP = dict(L_up=50, L_fore=-150, L_hand=-70, L_pose='open', R_up=50, R_fore=-150, R_hand=-70, R_pose='open')
POINT_PROD = dict(L_up=150, L_fore=12, L_hand=0, L_pose='point')
EXPLAIN = dict(L_up=20, L_fore=-70, L_hand=0, L_pose='open', R_up=20, R_fore=-70, R_hand=0, R_pose='open')
THUMB = dict(L_up=20, L_fore=-195, L_hand=0, L_pose='thumb')
SPREAD = dict(L_up=80, L_fore=-30, L_hand=-25, L_pose='open', R_up=80, R_fore=-30, R_hand=-25, R_pose='open')
HOLD = dict(L_up=28, L_fore=-98, L_hand=-12, L_pose='open', R_up=28, R_fore=-98, R_hand=-12, R_pose='open')
CALL = dict(R_up=30, R_fore=-110, R_hand=-20, R_pose='open')
THINK = dict(L_up=12, L_fore=-168, L_hand=0, L_pose='rest')
CAM0 = dict(zoom=1.0, fx=540, fy=960)
BASE = P(REST_L, REST_R, CAM0, look=0, lean=1.0, swayk=0, tilt=0, wave=0, explain=0)


def gesture_keys(kind, s, e):
    """シーン(開始s,終了e)の動作とカメラのキーフレーム"""
    d = e - s; k = []
    if kind == 'hello':
        k += [(s + 0.3, P(WAVE_R, REST_L, wave=1, tilt=-3)), (e - 0.05, P(WAVE_R, wave=1, tilt=-3))]
    elif kind == 'hook':
        k += [(s + 0.12, P(SURP, CAM0, wave=0, tilt=0, zoom=1.12, fy=760)), (s + 0.6, P(SURP, zoom=1.05, fy=800)),
              (e - 0.25, P(SURP, zoom=1.03)), (e + 0.1, P(REST_L, REST_R, CAM0))]
    elif kind in ('point', 'detail'):
        z = 1.12 if kind == 'detail' else 1.05
        k += [(s + 0.45, P(POINT_PROD, REST_R, look=-10, swayk=-2.0, tilt=-3, zoom=z, fx=500, fy=820)),
              (e - 0.1, P(POINT_PROD, look=-10, swayk=-2.0, tilt=-3, zoom=z + 0.03, fx=500, fy=820))]
    elif kind == 'explain':
        k += [(s + 0.5, P(EXPLAIN, CAM0, explain=1, look=0, swayk=0, tilt=0)), (e - 0.1, P(EXPLAIN, explain=1))]
    elif kind == 'push':
        mid = s + d * 0.42
        k += [(s + 0.4, P(EXPLAIN, explain=1, lean=1.035, zoom=1.06, fx=820, fy=1400)),
              (mid, P(EXPLAIN, REST_R, explain=0, lean=1.035)),
              (mid + 0.4, P(THUMB, lean=1.04, tilt=4, zoom=1.1, fx=820, fy=1400)),
              (e - 0.05, P(THUMB, lean=1.04, tilt=4, zoom=1.12, fx=820, fy=1400))]
    elif kind == 'price':
        k += [(s + 0.25, P(SPREAD, CAM0, look=0, tilt=0, lean=1.02, zoom=1.08, fx=540, fy=900, explain=0)),
              (e - 0.1, P(SPREAD, lean=1.02, zoom=1.12, fx=540, fy=900))]
    elif kind == 'hold':
        k += [(s + 0.4, P(HOLD, CAM0, look=0, tilt=0, zoom=1.06, fx=820, fy=1350)), (e - 0.1, P(HOLD, zoom=1.08, fx=820, fy=1350))]
    elif kind == 'call':
        k += [(s + 0.35, P(CALL, REST_L, CAM0, lean=1.05, look=0, tilt=-2, explain=0, zoom=1.05, fx=820, fy=1350)),
              (e - 0.1, P(CALL, REST_L, lean=1.05, tilt=-2, zoom=1.07, fx=820, fy=1350))]
    elif kind == 'think':
        k += [(s + 0.35, P(THINK, REST_R, CAM0, tilt=6, look=-6)), (e - 0.1, P(THINK, tilt=6, look=-6))]
    elif kind == 'doubletake':
        k += [(s + 0.15, P(REST_L, REST_R, CAM0, look=-12, tilt=-4)), (s + 0.45, P(look=12, tilt=4)),
              (s + 0.7, P(look=-12, tilt=-4)), (e, P(SURP, look=0, tilt=0, zoom=1.1, fy=800))]
    elif kind == 'bye':
        k += [(s + 0.35, P(REST_L, WAVE_R, CAM0, wave=1, look=0, tilt=-3, lean=1.0)), (e + TAIL, P(REST_L, WAVE_R, wave=1, tilt=-3))]
    return k


def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


class Timeline:
    def __init__(self, keys):
        full, cur = [], dict(BASE)
        for t, kw in sorted(keys, key=lambda x: x[0]):
            cur = dict(cur); cur.update(kw); full.append((t, cur))
        self.full = [(0.0, dict(BASE))] + full

    def at(self, t):
        f = self.full
        for i in range(len(f) - 1):
            t0, a = f[i]; t1, b = f[i + 1]
            if t0 <= t <= t1:
                u = smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1
                return {k: (a[k] if u < 0.5 else b[k]) if isinstance(a[k], str) else a[k] + (b[k] - a[k]) * u for k in a}
        return dict(f[-1][1]) if t > f[-1][0] else dict(f[0][1])


# ---------- 音声 ----------
def concat_audio(parts, starts, total, out):
    with wave.open(parts[0]) as w0:
        rate = w0.getframerate()
    buf = array.array('h', [0]) * int(total * rate)
    for p, st in zip(parts, starts):
        with wave.open(p) as w:
            a = array.array('h'); a.frombytes(w.readframes(w.getnframes()))
        o = int(st * rate)
        n = min(len(a), len(buf) - o)
        if n > 0:
            buf[o:o + n] = a[:n]
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(buf.tobytes())
    hop = rate // FPS
    rms = []
    for f in range(int(total * FPS)):
        seg = buf[f * hop:(f + 1) * hop]
        rms.append(math.sqrt(sum(x * x for x in seg) / max(1, len(seg))) if len(seg) else 0)
    peak = max(rms) or 1
    return [r / peak for r in rms]


def pick_bgm(item, total, work):
    choice = item.get('bgm', 'auto')
    if choice == 'none':
        return None, None, 'none'
    if choice != 'auto':
        f = ROOT / 'bgm' / choice
        if not f.exists():
            raise FileNotFoundError(f'BGMファイルがありません: bgm/{choice}')
        cred_file = ROOT / 'bgm' / 'credits.json'
        credits = json.loads(cred_file.read_text()) if cred_file.exists() else {}
        if choice not in credits:
            raise ValueError(f'bgm/credits.json に {choice} の出典・利用条件を書いてください')
        return f, credits[choice] or None, choice
    path = work / 'bgm.wav'
    info = bgm.compose(total, item['item_id'], str(path))
    return path, None, dict(type='auto', **info)


# ---------- 画面 ----------
def tb(s, x, y, size, anchor='middle', weight=900, fill='#FFFFFF', stroke=INK, sw=14, ls=1.25):
    o = ''
    for i, ln in enumerate(s.split('\n')):
        o += (f'<text x="{x:.1f}" y="{y + i * size * ls:.1f}" font-size="{size:.1f}" font-weight="{weight}" text-anchor="{anchor}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" paint-order="stroke">{ln}</text>')
    return o


def text_w(line, size):
    return sum(0.66 if ord(c) < 0x2E80 else 1.04 for c in line) * size


def fit(text, size, maxw):
    """一番長い行が maxw に収まるよう文字サイズを下げる"""
    longest = max(text.split('\n'), key=lambda l: text_w(l, 1))
    return min(size, maxw / max(1e-6, text_w(longest, 1)))


def ease(x):
    x = max(0, min(1, x)); return 1 - (1 - x) ** 3


def back(x):   # 少し行き過ぎて戻る(ポップ)
    x = max(0, min(1, x)); c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def price_badge(item):
    if item.get('status') == 'sold':
        return f"SOLD ¥{item['price_yen']:,}"
    if item.get('sale_type') == 'auction':
        sp = item.get('start_price_yen')
        return f"¥{sp:,}スタート" if sp else "オークション"
    return f"¥{item['price_yen']:,}"


SHOTS = {  # 写真番号, 注目点(0-1), 拡大率
    'full': (0, 0.5, 0.5, 1.0), 'full2': (1, 0.5, 0.5, 1.0), 'full3': (2, 0.5, 0.5, 1.0),
    'top': (0, 0.5, 0.22, 1.9), 'knee': (0, 0.5, 0.62, 1.8), 'hem': (0, 0.5, 0.86, 1.9),
}


class Video:
    def __init__(self, item, plan, scenes, chips, photos, total, levels):
        self.item, self.plan, self.scenes, self.chips, self.photos = item, plan, scenes, chips, photos
        self.total, self.levels = total, levels
        keys = []
        for sc in scenes:
            keys += gesture_keys(sc['gesture'], sc['start'], sc['end'])
        self.tl = Timeline(keys)
        self.nods = [sc['start'] + 0.25 for sc in scenes if sc['gesture'] in ('point', 'explain', 'detail', 'call', 'push')]
        self.blinks = [1.1 + 2.9 * i + (0.4 if i % 2 else 0) for i in range(int(total / 2.9) + 1)]
        self.hops = [sc['start'] + 0.3 for sc in scenes if sc['gesture'] in ('hook', 'price')]
        self.hops += [sc['end'] for sc in scenes if sc['gesture'] == 'doubletake']

    def scene_at(self, t):
        for sc in self.scenes:
            if t < sc['end'] + 0.12:
                return sc
        return self.scenes[-1]

    def pose(self, t):
        c = self.tl.at(t); sc = self.scene_at(t)
        st = dict(c); st['t'] = t; st['expr'] = sc['expr']
        st['sway'] = c['swayk'] + 1.1 * math.sin(2 * math.pi * 0.33 * t)
        st['shift'] = 3.0 * math.sin(2 * math.pi * 0.33 * t + 0.6)
        if c['wave'] > 0.5:
            st['R_fore'] += 16 * c['wave'] * math.sin(2 * math.pi * 2.0 * t)
            st['R_hand'] += 10 * c['wave'] * math.sin(2 * math.pi * 2.0 * t - 0.8)
        if c['explain'] > 0.01:
            st['L_fore'] += 7 * c['explain'] * math.sin(2 * math.pi * 0.9 * t)
            st['R_fore'] += 7 * c['explain'] * math.sin(2 * math.pi * 0.9 * t + 1.6)
            st['L_hand'] += 6 * c['explain'] * math.sin(2 * math.pi * 0.9 * t + 0.4)
        if st['L_pose'] == 'point':
            st['L_fore'] += 4 * max(0, math.sin(2 * math.pi * 1.4 * t)) ** 2
        if sc['gesture'] == 'price':   # 価格のところは手を広げてリズムよく揺らす
            st['L_up'] += 6 * math.sin(2 * math.pi * 1.6 * t); st['R_up'] += 6 * math.sin(2 * math.pi * 1.6 * t)
        nod = sum(6 * math.exp(-((t - n) / 0.16) ** 2) for n in self.nods)
        st['nod'] = nod
        st['tilt'] = c['tilt'] + 1.3 * math.sin(2 * math.pi * 0.45 * t)
        st['hop'] = sum(22 * math.exp(-((t - h) / 0.13) ** 2) for h in self.hops)
        st['ahoge'] = 5 * math.sin(2 * math.pi * 1.3 * t) + 0.6 * st['hop'] * math.sin(2 * math.pi * 3 * t) + nod * 1.2
        st['blink'] = any(0 <= t - b < 0.12 for b in self.blinks)
        f = min(int(t * FPS), len(self.levels) - 1)
        lv = self.levels[f] if f >= 0 else 0
        speaking = sc['start'] - 0.05 <= t <= sc['end']
        st['mouth'] = 'open' if (not speaking or lv > 0.18) else 'closed'
        return st, sc

    def photo_layer(self, sc, t, cx, cy, iw, ih):
        if not self.photos:
            return (f'<rect x="{cx-iw/2:.1f}" y="{cy-ih/2:.1f}" width="{iw:.1f}" height="{ih:.1f}" rx="22" fill="#E9E3D8"></rect>'
                    + tb('商品写真が入る位置', cx, cy, 54, 'middle', 700, '#8A7C68', '#E9E3D8', 0))
        idx, fxr, fyr, z = SHOTS.get(sc.get('shot', 'full'), SHOTS['full'])
        img = self.photos[idx % len(self.photos)]
        lt = t - sc['start']; d = max(0.6, sc['end'] - sc['start'])
        z = z * (1 + 0.06 * ease(lt / d))                 # ゆっくり寄る
        slide = (1 - ease(lt / 0.22)) * 90                 # カットの切り替わりで横から入る
        # 拡大の中心を注目点へ
        lim_x, lim_y = (z - 1) * iw / 2, (z - 1) * ih / 2   # 写真の端が見えない範囲で注目点へ寄せる
        px = cx - max(-lim_x, min(lim_x, (fxr - 0.5) * iw * z))
        py = cy - max(-lim_y, min(lim_y, (fyr - 0.5) * ih * z))
        return (f'<g clip-path="url(#ph)"><g transform="translate({px + slide:.1f} {py:.1f}) scale({z:.4f}) translate({-cx:.1f} {-cy:.1f})">'
                f'<image x="{cx-iw/2:.1f}" y="{cy-ih/2:.1f}" width="{iw:.1f}" height="{ih:.1f}" preserveAspectRatio="xMidYMid slice" href="{img}"></image></g></g>')

    def frame_svg(self, t):
        st, sc = self.pose(t)
        g = sc['gesture']; lt = t - sc['start']
        is_price = sc.get('telop') == 'price'
        s = ''
        # 背景と照明
        s += f'<rect width="{W}" height="{H}" fill="#F2EFE9"></rect>'
        s += (f'<radialGradient id="spot" cx="0.78" cy="0.7" r="0.55"><stop offset="0" stop-color="#FFF6DD" stop-opacity="0.95"></stop>'
              f'<stop offset="1" stop-color="#F2EFE9" stop-opacity="0"></stop></radialGradient><rect width="{W}" height="{H}" fill="url(#spot)"></rect>')
        if is_price:   # 価格のときは集中線のような光
            rot = (t * 25) % 360; a = ease(lt / 0.3)
            rays = ''.join(f'<path d="M540 760 L{540 + 1600*math.cos(math.radians(i*15+rot)):.0f} {760 + 1600*math.sin(math.radians(i*15+rot)):.0f} '
                           f'L{540 + 1600*math.cos(math.radians(i*15+rot+6)):.0f} {760 + 1600*math.sin(math.radians(i*15+rot+6)):.0f} Z" fill="#FFD84D"></path>' for i in range(24))
            s += f'<g opacity="{0.35*a:.2f}">{rays}</g>'
        # 商品写真
        pz = 1 + 0.02 * (t / self.total)
        cx, cy, pw, ph = 540, 700, 860 * pz, 860 * pz
        iw, ih = pw - 48, ph - 48
        s += f'<rect x="{cx-pw/2:.1f}" y="{cy-ph/2:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="36" fill="#FFFFFF" stroke="{INK}" stroke-width="6"></rect>'
        s += f'<clipPath id="ph"><rect x="{cx-iw/2:.1f}" y="{cy-ih/2:.1f}" width="{iw:.1f}" height="{ih:.1f}" rx="22"></rect></clipPath>'
        s += self.photo_layer(sc, t, cx, cy, iw, ih)
        if sc.get('shot') in ('top', 'knee', 'hem'):
            lab = {'top': 'ウエストまわり', 'knee': 'ひざ・色落ち', 'hem': '裾'}[sc['shot']]
            s += (f'<rect x="{cx-pw/2+40:.1f}" y="{cy+ph/2-110:.1f}" width="300" height="64" rx="32" fill="#B5452E"></rect>'
                  + tb(f'DETAIL・{lab}', cx - pw / 2 + 190, cy + ph / 2 - 66, 30, 'middle', 800, '#FFFFFF', INK, 0))
        s += (f'<rect x="{cx+pw/2-430:.1f}" y="{cy-ph/2-36:.1f}" width="430" height="84" rx="42" fill="{INK}"></rect>'
              + tb(price_badge(self.item), cx + pw / 2 - 215, cy - ph / 2 + 19, 36, 'middle', 800, '#FFD84D', INK, 0))
        # 訴求ラベル(シーンが進むごとに増える)
        for i, key in enumerate(('c1', 'c2', 'c3')):
            if key not in self.chips or i + 1 >= len(self.scenes):
                continue
            t0 = self.scenes[i + 1]['start']
            if t < t0:
                continue
            a = ease((t - t0) / 0.35); y = 1210 + i * 96; x = 110 - (1 - a) * 400
            hot = self.scenes.index(sc) == i + 1
            s += (f'<g opacity="{a:.2f}"><rect x="{x:.1f}" y="{y}" width="540" height="78" rx="39" fill="{"#B5452E" if hot else "#FFFFFF"}" stroke="{INK}" stroke-width="5"></rect>'
                  + tb(self.chips[key], x + 30, y + 52, 36, 'start', 800, '#FFFFFF' if hot else INK, INK, 0) + '</g>')
        # 古着くん(+商品を持つカード)
        s += f'<g transform="translate({CHAR_X} {CHAR_Y})">{rig.character(st)}'
        if g == 'hold' and self.photos:
            a = ease((lt - 0.2) / 0.3)
            if a > 0:
                s += (f'<g opacity="{a:.2f}" transform="translate(200 300) rotate(-4) scale({0.6 + 0.4*a:.3f})">'
                      f'<rect x="-95" y="-110" width="190" height="220" rx="10" fill="#FFFFFF" stroke="{INK}" stroke-width="4"></rect>'
                      f'<clipPath id="hc"><rect x="-82" y="-97" width="164" height="170" rx="6"></rect></clipPath>'
                      f'<image x="-82" y="-97" width="164" height="170" preserveAspectRatio="xMidYMid slice" clip-path="url(#hc)" href="{self.photos[0]}"></image></g>')
        s += '</g>'
        z, fx, fy = st['zoom'], st['fx'], st['fy']
        body = f'<g transform="translate({fx:.1f} {fy:.1f}) scale({z:.4f}) translate({-fx:.1f} {-fy:.1f})">{s}</g>'
        s = ''
        # テロップ(ズームの影響を受けない層)
        if sc.get('telop') == 'big':
            a = back(lt / 0.28); sz = fit(sc['caption'], 84, 960) * max(0.3, a)
            s += f'<g opacity="{min(1, lt/0.12):.2f}">' + tb(sc['caption'], W / 2, 380, sz, 'middle', 900, '#FFFFFF', '#B5452E', 22) + '</g>'
        elif is_price:
            a = back(lt / 0.32); shake = 6 * math.sin(lt * 70) * max(0, 1 - lt / 0.5)
            lines = sc['caption'].split('\n')
            main = next((l for l in lines if '¥' in l), lines[-1])
            sub = ' '.join(l for l in lines if l != main)
            s += f'<g transform="translate({540 + shake:.1f} 760) scale({max(0.2, a):.3f})">'
            if sub:
                s += tb(sub, 0, -120, fit(sub, 70, 900), 'middle', 900, '#FFFFFF', INK, 18)
            s += tb(main, 0, 40, fit(main, 132, 880), 'middle', 900, '#FFD84D', '#B5452E', 26) + '</g>'
        else:
            s += tb(sc['caption'], 370, 1610, fit(sc['caption'], 52, 640), 'middle', 900, '#FFFFFF', INK, 14)
        # カットの切り替わりの白フラッシュ
        if sc.get('telop') in ('big', 'price') and lt < 0.1:
            s += f'<rect width="{W}" height="{H}" fill="#FFFFFF" opacity="{0.55*(1-lt/0.1):.2f}"></rect>'
        body += s
        top = (f'<rect y="0" width="{W}" height="150" fill="{INK}"></rect>'
               + tb('古着くんの今日の一着', 60, 98, 52, 'start', 700, '#F4EFE6', INK, 0))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}" font-family="{FONT}">{V.DEFS}{body}{top}</svg>')


_VIDEO = None
def _render(args):
    i, d = args
    svg = os.path.join(d, f'f{i:05d}.svg'); png = svg[:-4] + '.png'
    with open(svg, 'w') as f:
        f.write(_VIDEO.frame_svg(i / FPS))
    subprocess.run(['rsvg-convert', svg, '-o', png], check=True)
    os.remove(svg)


def load_photos(item_dir):
    out = []
    for p in sorted(glob.glob(os.path.join(item_dir, 'photos', '*'))):
        ext = p.lower().rsplit('.', 1)[-1]
        if ext in ('jpg', 'jpeg', 'png'):
            mime = 'image/png' if ext == 'png' else 'image/jpeg'
            out.append(f'data:{mime};base64,' + base64.b64encode(open(p, 'rb').read()).decode())
    return out


def source_hash(item_dir):
    h = hashlib.sha256()
    it = json.loads((item_dir / 'item.json').read_text())
    for k in ('fetched_at', 'num_likes', 'num_comments', 'highest_bid_yen', 'total_bids', 'api_status'):
        it.pop(k, None)   # 反応の数字が変わっただけでは作り直さない
    h.update(json.dumps(it, sort_keys=True, ensure_ascii=False).encode())
    for p in sorted((item_dir / 'photos').glob('*')):
        if p.is_file():
            h.update(p.name.encode()); h.update(p.read_bytes())
    for f in ('build.py', 'script_gen.py', 'bgm.py', 'rig.py', 'sfx.py'):
        h.update((HERE / f).read_bytes())
    return h.hexdigest()[:16]


def history_patterns():
    f = ROOT / 'outputs' / 'pattern_history.json'
    return json.loads(f.read_text()) if f.exists() else []


def build(item_id, mock=False, skip_sold=False, variant=0, pattern=None):
    global _VIDEO
    item_dir = ROOT / 'items' / item_id
    item = json.loads((item_dir / 'item.json').read_text())
    if skip_sold and item.get('status') != 'on_sale':
        print('販売中でないためスキップ', item_id); return None
    out = ROOT / 'outputs' / item_id; out.mkdir(parents=True, exist_ok=True)
    work = ROOT / '.work' / item_id
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)

    hist = history_patterns()
    plan, scenes, chips = build_script(item, variant=variant, pattern=pattern, avoid=hist[-2:])
    print('演出パターン:', plan['pattern_name'], '候補:', plan['ranked'])
    # 音声(シーンごとに声色・速さ・抑揚・声量・間を変える)
    if mock:
        spk = (None, 'MOCK', 'MOCK', {})
    else:
        spk = tts.pick_speaker()
    styles = spk[3]
    t, parts, starts = 0.35, [], []
    for i, sc in enumerate(scenes):
        t += sc['pause'] if i else 0
        p = str(work / f'line{i:02d}.wav')
        if mock:
            dur = tts.mock_synth(sc['voice'], p)
        else:
            sid = styles.get(sc['style'], spk[0])
            dur = tts.synth(sc['voice'], sid, p, speed=sc['speed'], intonation=sc['intonation'], volume=sc['volume'])
        sc['start'], sc['end'] = t, t + dur
        parts.append(p); starts.append(t)
        t += dur
    total = scenes[-1]['end'] + TAIL
    levels = concat_audio(parts, starts, total, str(out / 'voice.wav'))
    # 効果音
    ev = []
    for sc in scenes:
        name = sc.get('sfx')
        if name == 'drum':
            ev.append((sc['start'] - 0.45, 'drum'))
        elif name:
            ev.append((sc['start'] - (0.15 if name == 'whoosh' else 0.02), name))
    sfx.track(ev, total, str(work / 'sfx.wav'), seed=int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % 1000)

    _VIDEO = Video(item, plan, scenes, chips, load_photos(str(item_dir)), total, levels)
    n = int(total * FPS)
    with ProcessPoolExecutor(mp_context=multiprocessing.get_context('fork')) as ex:
        list(ex.map(_render, [(i, str(work)) for i in range(n)], chunksize=8))
    mp4 = out / f'furugikun_{item_id}.mp4'
    music, music_credit, music_info = pick_bgm(item, total, work)
    vol = float(item.get('bgm_volume', 0.2))
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(work / 'f%05d.png'),
           '-i', str(out / 'voice.wav'), '-i', str(work / 'sfx.wav')]
    fc = ('[1:a]aresample=44100,aformat=channel_layouts=stereo,asplit=2[v1][v2];'
          '[2:a]volume=0.55[fx];')
    if music:
        cmd += ['-stream_loop', '-1', '-i', str(music)]
        fc += (f'[3:a]aresample=44100,aformat=channel_layouts=stereo,volume={vol},afade=t=out:st={max(0, total - 1.2):.2f}:d=1.2[m];'
               '[m][v1]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=350[md];'
               '[v2]volume=1.4[vv];[vv][md][fx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95[a]')
    else:
        fc += '[v2]volume=1.4[vv];[vv][fx]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]'
    cmd += ['-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', f'{total:.3f}', '-movflags', '+faststart', str(mp4)]
    subprocess.run(cmd, check=True)
    (out / 'script.json').write_text(json.dumps(dict(pattern=plan['pattern'], pattern_name=plan['pattern_name'],
                                                     candidates=plan['ranked'], speaker=spk[1], total_sec=round(total, 2),
                                                     bgm=music_info, scenes=scenes, chips=chips), ensure_ascii=False, indent=2))
    pj = posts.make_posts(item, plan, variant)
    pj['credits'] = [f"音声：{CREDIT}"] + ([f"BGM：{music_credit}"] if music_credit else [])
    (out / 'posts.json').write_text(json.dumps(pj, ensure_ascii=False, indent=2))
    (out / 'post.txt').write_text(pj['tiktok']['caption'] + '\n')
    if not mock:
        (out / 'source.hash').write_text(source_hash(item_dir))
        hist.append(plan['pattern'])
        (ROOT / 'outputs' / 'pattern_history.json').write_text(json.dumps(hist[-50:]))
    shutil.rmtree(work, ignore_errors=True)
    print('done', mp4, f'{total:.1f}s', plan['pattern_name'], 'speaker:', spk[1])
    return mp4


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else default
    return default


if __name__ == '__main__':
    skip = {arg('--variant'), arg('--pattern')}
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a not in skip]
    mock = '--mock-tts' in sys.argv
    variant = int(arg('--variant', 0) or 0)
    pattern = arg('--pattern')
    pending_mode = '--pending' in sys.argv or '--list-pending' in sys.argv
    if pending_mode:
        ids = []
        for p in sorted((ROOT / 'items').iterdir()):
            if not (p / 'item.json').exists():
                continue
            it = json.loads((p / 'item.json').read_text())
            if it.get('status') != 'on_sale':
                continue
            hf = ROOT / 'outputs' / p.name / 'source.hash'
            if not hf.exists() or hf.read_text().strip() != source_hash(p):
                ids.append(p.name)
        if '--list-pending' in sys.argv:
            print(' '.join(ids)); sys.exit(0)
        print('作成対象:', ids or 'なし')
    else:
        ids = args
    for i in ids:
        build(i, mock, skip_sold=pending_mode, variant=variant, pattern=pattern)
