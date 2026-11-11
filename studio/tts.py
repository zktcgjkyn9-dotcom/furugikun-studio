"""VOICEVOXエンジン(HTTP)で台詞ごとに音声を作る。

利用規約: 生成音声を使う作品には「VOICEVOX:白上虎太郎」のクレジットが必要。
"""
import json, os, urllib.parse, urllib.request, wave, io, math, struct

ENGINE = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
SPEAKER_NAME = os.environ.get("VOICEVOX_SPEAKER", "白上虎太郎")
STYLE_NAME = os.environ.get("VOICEVOX_STYLE", "ふつう")


def _get(path):
    with urllib.request.urlopen(ENGINE + path, timeout=60) as r:
        return json.loads(r.read())


def _post(path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(ENGINE + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = r.read()
    return out if raw else json.loads(out)


def pick_speaker():
    speakers = _get("/speakers")
    for sp in speakers:
        if sp["name"] == SPEAKER_NAME:
            for st in sp["styles"]:
                if st["name"] == STYLE_NAME:
                    return st["id"], sp["name"], st["name"]
            st = sp["styles"][0]
            return st["id"], sp["name"], st["name"]
    raise RuntimeError(f"話者 {SPEAKER_NAME} が見つかりません: {[s['name'] for s in speakers]}")


def synth(text, speaker_id, path, speed=1.12, intonation=1.2):
    q = _post("/audio_query?" + urllib.parse.urlencode({"text": text, "speaker": speaker_id}))
    q["speedScale"] = speed
    q["intonationScale"] = intonation
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.05
    wav = _post("/synthesis?" + urllib.parse.urlencode({"speaker": speaker_id}), q, raw=True)
    with open(path, "wb") as f:
        f.write(wav)
    return wav_duration(path)


def wav_duration(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def mock_synth(text, path, rate=24000):
    """エンジンが無い環境のテスト用:文字数に比例した長さの小さな音(本番では使わない)"""
    dur = 0.35 + 0.13 * len(text)
    n = int(dur * rate)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 5 * i / rate)
            frames += struct.pack("<h", int(3000 * env * math.sin(2 * math.pi * 220 * i / rate)))
        w.writeframes(bytes(frames))
    return dur
