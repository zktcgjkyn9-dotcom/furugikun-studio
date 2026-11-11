"""古着くん専用BGMをプログラムで作曲する(外部の音源を使わないので著作権・クレジットの心配なし)。

ゆったりしたローファイ風: エレピ風の和音 + ベース + 軽いドラム。
商品IDから曲調(テンポ・コード進行・音色)を決めるので、動画ごとに少しずつ変わる。
"""
import hashlib, wave
import numpy as np

SR = 44100

PROGRESSIONS = [
    # (コード名は参考)  各コードの構成音(MIDI番号)
    [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]],   # Fmaj7 Em7 Dm7 Cmaj7
    [[48, 52, 55, 59], [45, 48, 52, 55], [50, 53, 57, 60], [43, 47, 50, 53]],   # Cmaj7 Am7 Dm7 G7
    [[45, 48, 52, 55], [50, 53, 57, 60], [43, 47, 50, 53], [48, 52, 55, 59]],   # Am7 Dm7 G7 Cmaj7
    [[53, 57, 60, 64], [55, 59, 62, 65], [52, 55, 59, 62], [45, 48, 52, 55]],   # Fmaj7 G7 Em7 Am7
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def epiano(freq, dur, amp=0.12):
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-t * 1.6) * (1 - np.exp(-t * 80))
    tone = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 4)
            + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 6))
    trem = 1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)
    return amp * tone * env * trem


def bass(freq, dur, amp=0.22):
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 200))
    return amp * (np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * 2 * freq * t)) * env


def kick(amp=0.5):
    t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat(rng, amp=0.05):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(4) / 4, mode='same')  # 高い音だけ残す
    return amp * noise * np.exp(-t * 60)


def snare(rng, amp=0.12):
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    return amp * (rng.standard_normal(n) * np.exp(-t * 22) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30))


def add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i]


def compose(seconds, seed_text='furugikun', path='bgm.wav'):
    h = int(hashlib.sha256(seed_text.encode()).hexdigest(), 16)
    rng = np.random.default_rng(h % (2 ** 32))
    bpm = [84, 88, 92, 96][h % 4]
    prog = PROGRESSIONS[(h // 4) % len(PROGRESSIONS)]
    beat = 60 / bpm
    bar = beat * 4
    total = seconds + 1.0
    L = np.zeros(int(total * SR)); R = np.zeros(int(total * SR))
    n_bars = int(total / bar) + 1
    for b in range(n_bars):
        t0 = b * bar
        chord = prog[b % len(prog)]
        # 和音(少しずらして弾く)
        for k, m in enumerate(chord):
            s = epiano(hz(m + 12), bar * 1.1)
            add(L, s * (0.9 if k % 2 else 1.1), t0 + 0.012 * k)
            add(R, s * (1.1 if k % 2 else 0.9), t0 + 0.012 * k)
        # 2拍目裏で軽く刻む
        for k, m in enumerate(chord[1:]):
            s = epiano(hz(m + 12), beat * 0.9, amp=0.06)
            add(L, s, t0 + beat * 2.5 + 0.01 * k); add(R, s, t0 + beat * 2.5 + 0.01 * k)
        # ベース
        root = chord[0] - 12
        for at, m in [(0, root), (beat * 1.5, root), (beat * 2, root + 7), (beat * 3.5, root + 12)]:
            s = bass(hz(m), beat * 0.9)
            add(L, s, t0 + at); add(R, s, t0 + at)
        # ドラム(少しハネる)
        for i in range(8):
            swing = 0.03 * beat if i % 2 else 0
            hs = hat(rng)
            add(L, hs * 0.8, t0 + i * beat / 2 + swing); add(R, hs * 1.2, t0 + i * beat / 2 + swing)
        for at in (0, beat * 2.5):
            k = kick(); add(L, k, t0 + at); add(R, k, t0 + at)
        for at in (beat, beat * 3):
            s = snare(rng); add(L, s, t0 + at); add(R, s, t0 + at)
    # ローファイ感:軽いこもり + レコードのノイズ
    kern = np.ones(6) / 6
    L = np.convolve(L, kern, mode='same'); R = np.convolve(R, kern, mode='same')
    crackle = (rng.random(len(L)) > 0.9993) * rng.standard_normal(len(L)) * 0.03
    L += crackle; R += crackle
    # 頭とお尻をフェード
    n = int(seconds * SR)
    L, R = L[:n], R[:n]
    fi, fo = int(0.4 * SR), int(1.2 * SR)
    ramp = np.ones(n); ramp[:fi] = np.linspace(0, 1, fi); ramp[-fo:] = np.linspace(1, 0, fo)
    L *= ramp; R *= ramp
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
    st = np.stack([L, R], axis=1) / peak * 0.8
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())
    return dict(bpm=bpm, progression=(h // 4) % len(PROGRESSIONS))


if __name__ == '__main__':
    import sys
    print(compose(float(sys.argv[1]) if len(sys.argv) > 1 else 20, sys.argv[2] if len(sys.argv) > 2 else 'test', 'bgm_test.wav'))
