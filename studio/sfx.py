"""効果音をプログラムで作る(外部音源なし)。44.1kHzステレオのnumpy配列を返す。"""
import numpy as np

SR = 44100


def _t(d):
    return np.arange(int(d * SR)) / SR


def _st(x):
    return np.stack([x, x], axis=1)


def pop():
    t = _t(0.12); f = 900 * np.exp(-t * 25) + 300
    return _st(0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35))


def whoosh(rng):
    t = _t(0.35); n = rng.standard_normal(len(t))
    k = np.ones(12) / 12; n = n - np.convolve(n, k, mode="same")
    env = np.sin(np.pi * np.clip(t / 0.35, 0, 1)) ** 2
    return np.stack([n * env * 0.25 * (1 - t / 0.35), n * env * 0.25 * (t / 0.35)], axis=1)


def ding():
    t = _t(1.0)
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1568, 0.5), (3136, 0.2), (4704, 0.08)))
    return _st(0.45 * x * np.exp(-t * 4.5))


def drum(rng):
    """ドラムロール0.6秒 → シンバル"""
    roll = np.zeros(int(0.6 * SR))
    for i in range(18):
        s = int(i * 0.6 / 18 * SR); n = int(0.05 * SR)
        hit = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 60) * (0.15 + 0.25 * i / 18)
        roll[s:s + n] += hit[:len(roll) - s]
    t = _t(1.4); cym = rng.standard_normal(len(t)); cym = cym - np.convolve(cym, np.ones(3) / 3, mode="same")
    cym = 0.35 * cym * np.exp(-t * 2.8)
    kick = 0.7 * np.sin(2 * np.pi * np.cumsum(60 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 8)
    return _st(np.concatenate([roll, cym + kick]))


def boing():
    t = _t(0.5); f = 220 + 160 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4)
    return _st(0.45 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5))


def shutter(rng):
    a = rng.standard_normal(int(0.03 * SR)) * 0.35
    gap = np.zeros(int(0.05 * SR))
    b = rng.standard_normal(int(0.04 * SR)) * 0.3 * np.exp(-np.arange(int(0.04 * SR)) / SR * 50)
    return _st(np.concatenate([a, gap, b]))


def make(name, rng):
    return {"pop": pop, "ding": ding, "boing": boing}.get(name, lambda: None)() if name in ("pop", "ding", "boing") \
        else {"whoosh": whoosh, "drum": drum, "shutter": shutter}[name](rng)


def track(events, total, path, seed=0):
    """events: [(秒, 効果音名)] を並べた効果音トラックをwavで保存"""
    import wave
    rng = np.random.default_rng(seed)
    buf = np.zeros((int((total + 2) * SR), 2))
    for at, name in events:
        if not name:
            continue
        s = make(name, rng); i = int(max(0, at) * SR)
        j = min(len(buf), i + len(s)); buf[i:j] += s[:j - i]
    buf = buf[:int(total * SR)]
    buf = np.clip(buf, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype("<i2").tobytes())
