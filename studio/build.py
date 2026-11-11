"""古着くん 商品紹介ショート動画を作る。

使い方: python studio/build.py <item_id> [--mock-tts]
入力:  items/<item_id>/item.json, items/<item_id>/photos/*.jpg(任意)
出力:  outputs/<item_id>/furugikun_<item_id>.mp4, voice.wav, script.json, post.txt
"""
import sys, os, json, math, wave, array, base64, glob, hashlib, subprocess, pathlib, shutil
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import views as V, rig, tts, bgm
from script_gen import build_script

W, H, FPS = 1080, 1920, 30
INK = '#2A1E18'; FONT = 'Noto Sans CJK JP'
GAP = 0.2          # 台詞と台詞の間
TAIL = 0.7         # 最後の余韻
CREDIT = 'VOICEVOX:白上虎太郎'

# ---------- ポーズ ----------
REST_L = dict(L_up=8, L_fore=0, L_hand=0, L_pose='rest')
REST_R = dict(R_up=8, R_fore=0, R_hand=0, R_pose='rest')
WAVE_R = dict(R_up=150, R_fore=22, R_hand=0, R_pose='open')
SURP = dict(L_up=50, L_fore=-150, L_hand=-70, L_pose='open', R_up=50, R_fore=-150, R_hand=-70, R_pose='open')
POINT_PROD = dict(L_up=150, L_fore=12, L_hand=0, L_pose='point')
EXPLAIN = dict(L_up=20, L_fore=-70, L_hand=0, L_pose='open', R_up=20, R_fore=-70, R_hand=0, R_pose='open')
THUMB = dict(L_up=20, L_fore=-195, L_hand=0, L_pose='thumb')
POINT_DOWN = dict(L_up=55, L_fore=12, L_hand=0, L_pose='point')
CAM0 = dict(zoom=1.0, fx=540, fy=960)
def P(*ds, **kw):
    out = {}
    for d in ds:
        out.update(d)
    out.update(kw)
    return out


BASE = P(REST_L, REST_R, CAM0, look=0, lean=1.0, swayk=0, tilt=0, wave=0, explain=0)


def gesture_keys(kind, s, e):
    """シーン(開始s,終了e)の動作キーフレーム"""
    d = e - s
    k = []
    if kind == 'hello':
        k += [(s + 0.3, P(WAVE_R, wave=1, tilt=-3)), (e - 0.05, P(WAVE_R, wave=1, tilt=-3))]
    elif kind == 'hook':
        k += [(s + 0.25, P(SURP, wave=0, tilt=0)), (e - 0.3, P(SURP)), (e + 0.05, P(REST_L, REST_R))]
    elif kind == 'p1':
        k += [(s + 0.5, P(POINT_PROD, REST_R, look=-10, swayk=-2.0, tilt=-3, zoom=1.06, fx=420, fy=900)),
              (e - 0.1, P(POINT_PROD, look=-10, swayk=-2.0, tilt=-3, zoom=1.06, fx=420, fy=900))]
    elif kind == 'p2':
        k += [(s + 0.55, P(EXPLAIN, CAM0, explain=1, look=0, swayk=0, tilt=0)), (e - 0.1, P(EXPLAIN, explain=1))]
    elif kind == 'push':
        mid = s + d * 0.45
        k += [(s + 0.45, P(EXPLAIN, explain=1, lean=1.035, zoom=1.08, fx=840, fy=1450)),
              (mid, P(EXPLAIN, REST_R, explain=0, lean=1.035)),
              (mid + 0.45, P(THUMB, lean=1.035, tilt=4)),
              (e - 0.05, P(THUMB, lean=1.035, tilt=4, zoom=1.08, fx=840, fy=1450))]
    elif kind == 'cta':
        k += [(s + 0.4, P(POINT_DOWN, REST_R, CAM0, lean=1.0, look=-6, tilt=-2)), (e - 0.1, P(POINT_DOWN, look=-6, tilt=-2))]
    elif kind == 'bye':
        k += [(s + 0.35, P(REST_L, WAVE_R, wave=1, look=0, tilt=-3)), (e + TAIL, P(REST_L, WAVE_R, wave=1, tilt=-3))]
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
        if t <= f[0][0]:
            return dict(f[0][1])
        for i in range(len(f) - 1):
            t0, a = f[i]; t1, b = f[i + 1]
            if t0 <= t <= t1:
                u = smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1
                return {k: (a[k] if u < 0.5 else b[k]) if isinstance(a[k], str) else a[k] + (b[k] - a[k]) * u for k in a}
        return dict(f[-1][1])


# ---------- 音声 ----------
def concat_audio(parts, starts, total, out):
    """parts: wavファイル, starts: 開始秒。無音で埋めて1本にする。口パク用の音量も返す"""
    with wave.open(parts[0]) as w0:
        rate, width, ch = w0.getframerate(), w0.getsampwidth(), w0.getnchannels()
    buf = array.array('h', [0]) * int(total * rate)
    for p, st in zip(parts, starts):
        with wave.open(p) as w:
            a = array.array('h'); a.frombytes(w.readframes(w.getnframes()))
        o = int(st * rate)
        for i, v in enumerate(a):
            if o + i < len(buf):
                buf[o + i] = v
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(buf.tobytes())
    # フレームごとの音量(RMS)
    hop = rate // FPS
    rms = []
    for f in range(int(total * FPS)):
        seg = buf[f * hop:(f + 1) * hop]
        rms.append(math.sqrt(sum(x * x for x in seg) / max(1, len(seg))) if len(seg) else 0)
    peak = max(rms) or 1
    return [r / peak for r in rms]


# ---------- 画面 ----------
def tb(s, x, y, size, anchor='middle', weight=900, fill='#FFFFFF', stroke=INK, sw=14):
    o = ''
    for i, ln in enumerate(s.split('\n')):
        o += (f'<text x="{x}" y="{y + i * size * 1.25:.1f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" paint-order="stroke">{ln}</text>')
    return o


def ease(x):
    x = max(0, min(1, x)); return 1 - (1 - x) ** 3


def price_label(item):
    p = f"¥{item['price_yen']:,}"
    return f"{p}〜 オークション" if item.get('sale_type') == 'auction' else p


class Video:
    def __init__(self, item, scenes, chips, photos, total, levels):
        self.item, self.scenes, self.chips, self.photos = item, scenes, chips, photos
        self.total, self.levels = total, levels
        keys = []
        for sc in scenes:
            keys += gesture_keys(sc['kind'], sc['start'], sc['end'])
        self.tl = Timeline(keys)
        self.nods = [sc['start'] + 0.25 for sc in scenes if sc['kind'] in ('p1', 'p2', 'push', 'cta')]
        self.nods += [(sc['start'] + sc['end']) / 2 for sc in scenes if sc['kind'] in ('p2',)]
        self.blinks = [1.1 + 2.9 * i + (0.4 if i % 2 else 0) for i in range(int(total / 2.9) + 1)]
        hook = next((sc for sc in scenes if sc['kind'] == 'hook'), None)
        self.hop_t = hook['start'] + 0.35 if hook else -10

    def scene_at(self, t):
        for sc in self.scenes:
            if t < sc['end'] + GAP:
                return sc
        return self.scenes[-1]

    def pose(self, t):
        c = self.tl.at(t)
        sc = self.scene_at(t)
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
        nod = sum(6 * math.exp(-((t - n) / 0.16) ** 2) for n in self.nods)
        st['nod'] = nod
        st['tilt'] = c['tilt'] + 1.3 * math.sin(2 * math.pi * 0.45 * t)
        st['hop'] = 22 * math.exp(-((t - self.hop_t) / 0.13) ** 2)
        st['ahoge'] = 5 * math.sin(2 * math.pi * 1.3 * t) + 0.6 * st['hop'] * math.sin(2 * math.pi * 3 * t) + nod * 1.2
        st['blink'] = any(0 <= t - b < 0.12 for b in self.blinks)
        f = min(int(t * FPS), len(self.levels) - 1)
        lv = self.levels[f] if f >= 0 else 0
        speaking = sc['start'] - 0.05 <= t <= sc['end']
        st['mouth'] = 'open' if (not speaking or lv > 0.18) else 'closed'
        return st, sc

    def frame_svg(self, t):
        st, line = self.pose(t)
        kind = line['kind']; lt = t - line['start']
        s = f'<rect width="{W}" height="{H}" fill="#F2EFE9"></rect>'
        pz = 1 + 0.03 * (t / self.total)
        cx, cy, pw, ph = 540, 700, 860 * pz, 860 * pz
        s += f'<rect x="{cx-pw/2:.1f}" y="{cy-ph/2:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="36" fill="#FFFFFF" stroke="{INK}" stroke-width="6"></rect>'
        ix, iy, iw, ih = cx - pw / 2 + 24, cy - ph / 2 + 24, pw - 48, ph - 48
        if self.photos:
            # シーンごとに写真を切り替え、ゆっくり寄る
            idx = min(self.scenes.index(line), len(self.scenes) - 1) % len(self.photos)
            kb = 1 + 0.06 * ease(lt / max(0.5, line['end'] - line['start']))
            s += (f'<clipPath id="ph"><rect x="{ix:.1f}" y="{iy:.1f}" width="{iw:.1f}" height="{ih:.1f}" rx="22"></rect></clipPath>'
                  f'<g clip-path="url(#ph)"><g transform="translate({cx} {cy}) scale({kb:.4f}) translate({-cx} {-cy})">'
                  f'<image x="{ix:.1f}" y="{iy:.1f}" width="{iw:.1f}" height="{ih:.1f}" preserveAspectRatio="xMidYMid slice" href="{self.photos[idx]}"></image></g></g>')
        else:
            s += f'<rect x="{ix:.1f}" y="{iy:.1f}" width="{iw:.1f}" height="{ih:.1f}" rx="22" fill="#E9E3D8"></rect>'
            s += tb('商品写真が入る位置', cx, cy, 54, 'middle', 700, '#8A7C68', '#E9E3D8', 0)
        s += (f'<rect x="{cx+pw/2-420:.1f}" y="{cy-ph/2-36:.1f}" width="420" height="84" rx="42" fill="{INK}"></rect>'
              + tb(price_label(self.item), cx + pw / 2 - 210, cy - ph / 2 + 19, 36, 'middle', 800, '#F4EFE6', INK, 0))
        order = [k for k in ('p1', 'p2', 'push') if k in self.chips]
        for i, k in enumerate(order):
            sc = next((x for x in self.scenes if x['kind'] == k), None)
            if not sc or t < sc['start']:
                continue
            a = ease((t - sc['start']) / 0.35); y = 1210 + i * 96; x = 110 - (1 - a) * 400; hot = k == kind
            s += (f'<g opacity="{a:.2f}"><rect x="{x:.1f}" y="{y}" width="540" height="78" rx="39" fill="{"#B5452E" if hot else "#FFFFFF"}" stroke="{INK}" stroke-width="5"></rect>'
                  + tb(self.chips[k], x + 30, y + 52, 36, 'start', 800, '#FFFFFF' if hot else INK, INK, 0) + '</g>')
        s += f'<g transform="translate(640 1075)">{rig.character(st)}</g>'
        if kind == 'hook':
            a = ease(lt / 0.25); sz = 76 * (0.7 + 0.3 * a)
            s += f'<g opacity="{a:.2f}">' + tb(line['caption'], W / 2, 400, sz, 'middle', 900, '#FFFFFF', '#B5452E', 20) + '</g>'
        else:
            s += tb(line['caption'], 390, 1600 if kind == 'cta' else 1640, 54, 'middle', 900, '#FFFFFF', INK, 14)
        z, fx, fy = st['zoom'], st['fx'], st['fy']
        body = f'<g transform="translate({fx:.1f} {fy:.1f}) scale({z:.4f}) translate({-fx:.1f} {-fy:.1f})">{s}</g>'
        top = (f'<rect y="0" width="{W}" height="150" fill="{INK}"></rect>'
               + tb('古着くんの今日の一着', 60, 98, 52, 'start', 700, '#F4EFE6', INK, 0)
               + tb(CREDIT, 30, H - 24, 26, 'start', 700, '#5A4334', '#F2EFE9', 6))
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


def pick_bgm(item, total, work):
    """item.json の bgm: "auto"(既定・自動作曲) / "none"(なし) / bgm/フォルダのファイル名"""
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


def source_hash(item_dir):
    h = hashlib.sha256()
    for p in [item_dir / 'item.json'] + sorted((item_dir / 'photos').glob('*')):
        if p.is_file():
            h.update(p.name.encode()); h.update(p.read_bytes())
    for f in ('build.py', 'script_gen.py', 'bgm.py', 'rig.py'):
        h.update((HERE / f).read_bytes())
    return h.hexdigest()[:16]


def build(item_id, mock=False):
    global _VIDEO
    item_dir = ROOT / 'items' / item_id
    item = json.loads((item_dir / 'item.json').read_text())
    if item.get('status') == 'sold':
        print('売り切れのためスキップ', item_id); return None
    out = ROOT / 'outputs' / item_id; out.mkdir(parents=True, exist_ok=True)
    work = ROOT / '.work' / item_id
    shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)

    scenes, chips = build_script(item)
    # 音声
    if mock:
        spk = (None, 'MOCK', 'MOCK')
    else:
        spk = tts.pick_speaker()
    t, parts, starts = 0.4, [], []
    for i, sc in enumerate(scenes):
        p = str(work / f'line{i:02d}.wav')
        dur = tts.mock_synth(sc['voice'], p) if mock else tts.synth(sc['voice'], spk[0], p)
        sc['start'], sc['end'] = t, t + dur
        parts.append(p); starts.append(t)
        t += dur + GAP
    total = scenes[-1]['end'] + TAIL
    levels = concat_audio(parts, starts, total, str(out / 'voice.wav'))

    _VIDEO = Video(item, scenes, chips, load_photos(str(item_dir)), total, levels)
    n = int(total * FPS)
    with ProcessPoolExecutor(mp_context=multiprocessing.get_context('fork')) as ex:
        list(ex.map(_render, [(i, str(work)) for i in range(n)], chunksize=8))
    mp4 = out / f'furugikun_{item_id}.mp4'
    music, music_credit, music_info = pick_bgm(item, total, work)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(work / 'f%05d.png'),
           '-i', str(out / 'voice.wav')]
    if music:
        # 声が出ている間はBGMを自動で下げる(ダッキング)
        vol = float(item.get('bgm_volume', 0.22))
        cmd += ['-stream_loop', '-1', '-i', str(music), '-filter_complex',
                '[1:a]aresample=44100,aformat=channel_layouts=stereo,asplit=2[v1][v2];'
                f'[2:a]aresample=44100,aformat=channel_layouts=stereo,volume={vol},afade=t=out:st={max(0, total - 1.2):.2f}:d=1.2[m];'
                '[m][v1]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=350[md];'
                '[v2]volume=1.4[vv];[vv][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]',
                '-map', '0:v', '-map', '[a]']
    cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '160k', '-t', f'{total:.3f}', '-movflags', '+faststart', str(mp4)]
    subprocess.run(cmd, check=True)
    (out / 'script.json').write_text(json.dumps(dict(speaker=spk[1], style=spk[2], total_sec=round(total, 2), bgm=music_info,
                                                     scenes=scenes, chips=chips), ensure_ascii=False, indent=2))
    tags = ' '.join(f'#{x}' for x in [item.get('brand', ''), '古着', item.get('category', '')] if x)
    credits = f"音声：{CREDIT}" + (f"\nBGM：{music_credit}" if music_credit else "")
    (out / 'post.txt').write_text(f"{item['title']}\n{price_label(item)}\n\n{tags}\n\n{credits}\n")
    if not mock:
        (out / 'source.hash').write_text(source_hash(item_dir))
    shutil.rmtree(work, ignore_errors=True)
    print('done', mp4, f'{total:.1f}s', 'speaker:', spk[1], spk[2])
    return mp4


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    mock = '--mock-tts' in sys.argv
    if '--pending' in sys.argv:
        ids = []
        for p in sorted((ROOT / 'items').iterdir()):
            if not (p / 'item.json').exists():
                continue
            hf = ROOT / 'outputs' / p.name / 'source.hash'
            if not hf.exists() or hf.read_text().strip() != source_hash(p):
                ids.append(p.name)
        print('作成対象:', ids or 'なし')
    else:
        ids = args or [p.name for p in (ROOT / 'items').iterdir() if (p / 'item.json').exists()]
    for i in ids:
        build(i, mock)
