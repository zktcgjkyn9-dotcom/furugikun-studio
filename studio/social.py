"""投稿の予定管理・承認・自動投稿・成果の記録・分析・管理画面(STATUS.md)。

  python studio/social.py plan          … 新しくできた動画を投稿予定に入れる
  python studio/social.py approve <ID|all>  … 投稿予定を承認する
  python studio/social.py post          … 時間が来た承認済みの投稿を実行(認証情報がなければ実行しない)
  python studio/social.py metrics       … 投稿済みXの反応を取得
  python studio/social.py analyze       … 演出パターンごとの成果を集計し、次回の選び方に反映
  python studio/social.py status        … STATUS.md(管理画面)を作る

認証情報は GitHub の Secrets(X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET,
TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / TIKTOK_REFRESH_TOKEN)から読む。ファイルには書かない。
"""
import sys, os, json, time, hmac, hashlib, base64, uuid, urllib.parse, urllib.request, urllib.error, pathlib
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))
QUEUE = ROOT / "posting" / "queue.json"
HISTORY = ROOT / "posting" / "history.jsonl"
CONFIG = ROOT / "posting" / "config.json"
DEFAULT_CONFIG = {
    "auto_approve": False,                # True にすると確認なしで投稿する
    "x_slots": ["08:30", "12:30", "21:00"],
    "tiktok_slots": ["19:30"],
    "x_max_per_day": 3,
    "tiktok_max_per_day": 1,
    "x_max_per_month": 90,                # 予算ガード(X API は従量課金)
    "max_attempts": 3,
}


def now():
    return datetime.now(JST)


def load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def config():
    c = dict(DEFAULT_CONFIG)
    c.update(load(CONFIG, {}))
    if not CONFIG.exists():
        save(CONFIG, c)
    return c


def item(i):
    p = ROOT / "items" / i / "item.json"
    return json.loads(p.read_text()) if p.exists() else {}


def log(event):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a") as f:
        f.write(json.dumps(dict(at=now().isoformat(timespec="seconds"), **event), ensure_ascii=False) + "\n")


# ---------- 予定づくり ----------
def next_slot(slots, taken, per_day, start):
    d = start
    for _ in range(30):
        day = d.date()
        for s in slots:
            h, m = map(int, s.split(":"))
            t = datetime(day.year, day.month, day.day, h, m, tzinfo=JST)
            if t <= start or t.isoformat() in taken:
                continue
            if sum(1 for x in taken if x[:10] == day.isoformat()) >= per_day:
                break
            return t
        d = datetime(day.year, day.month, day.day, tzinfo=JST) + timedelta(days=1)
    return start + timedelta(days=1)


def plan():
    c = config(); q = load(QUEUE, [])
    have = {(e["item_id"], e["platform"], e.get("variant_key")) for e in q}
    for out in sorted((ROOT / "outputs").glob("m*/posts.json")):
        pj = json.loads(out.read_text()); iid = pj["item_id"]; it = item(iid)
        if it.get("status") != "on_sale":
            continue
        vkey = pj.get("generated_at", "")
        for e in q:   # 動画を作り直した商品は、古い版の承認待ちを取り下げる
            if e["item_id"] == iid and e.get("variant_key") != vkey and e["status"] == "awaiting_approval":
                e["status"] = "superseded"
        if (iid, "tiktok", vkey) not in have:
            taken = [e["scheduled_at"] for e in q if e["platform"] == "tiktok"]
            q.append(dict(id=uuid.uuid4().hex[:8], item_id=iid, platform="tiktok", variant_key=vkey,
                          video=f"outputs/{iid}/furugikun_{iid}.mp4", text=pj["tiktok"]["caption"], pattern=pj["pattern_name"],
                          scheduled_at=next_slot(c["tiktok_slots"], taken, c["tiktok_max_per_day"], now()).isoformat(),
                          status="approved" if c["auto_approve"] else "awaiting_approval", attempts=0, error=None))
        if (iid, "x", vkey) not in have and pj.get("x"):
            end = it.get("auction_end")
            taken = [e["scheduled_at"] for e in q if e["platform"] == "x"]
            t = next_slot(c["x_slots"], taken, c["x_max_per_day"], now())
            if end and t.isoformat() >= end:
                continue   # 終了後になる投稿は作らない
            x = pj["x"][0]
            q.append(dict(id=uuid.uuid4().hex[:8], item_id=iid, platform="x", variant_key=vkey, angle=x["angle"], text=x["text"],
                          scheduled_at=t.isoformat(), status="approved" if c["auto_approve"] else "awaiting_approval",
                          attempts=0, error=None))
    save(QUEUE, q)
    print("投稿予定", len(q), "件")


def approve(target):
    q = load(QUEUE, []); n = 0
    for e in q:
        if e["status"] == "awaiting_approval" and target in ("all", e["id"], e["item_id"]):
            e["status"] = "approved"; n += 1
    save(QUEUE, q); print("承認", n, "件")


# ---------- X ----------
def x_creds():
    keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    v = [os.environ.get(k) for k in keys]
    return v if all(v) else None


def oauth1_header(method, url, creds, params=None):
    ck, cs, tk, ts = creds
    oauth = {"oauth_consumer_key": ck, "oauth_nonce": uuid.uuid4().hex, "oauth_signature_method": "HMAC-SHA1",
             "oauth_timestamp": str(int(time.time())), "oauth_token": tk, "oauth_version": "1.0"}
    allp = dict(oauth, **(params or {}))
    enc = lambda s: urllib.parse.quote(str(s), safe="~")
    base = "&".join([method, enc(url), enc("&".join(f"{enc(k)}={enc(allp[k])}" for k in sorted(allp)))])
    key = f"{enc(cs)}&{enc(ts)}"
    oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{enc(k)}="{enc(v)}"' for k, v in sorted(oauth.items()))


def x_post(text, creds):
    url = "https://api.x.com/2/tweets"
    req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(), method="POST",
                                 headers={"Authorization": oauth1_header("POST", url, creds), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["data"]["id"]


def x_metrics(ids, creds):
    url = "https://api.x.com/2/tweets"
    params = {"ids": ",".join(ids), "tweet.fields": "public_metrics,non_public_metrics,created_at"}
    full = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"Authorization": oauth1_header("GET", url, creds, params)})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("data", [])


# ---------- TikTok(下書きとして受信箱へ送る) ----------
def tiktok_token():
    ck, cs, rt = (os.environ.get(k) for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"))
    if not (ck and cs and rt):
        return None
    data = urllib.parse.urlencode({"client_key": ck, "client_secret": cs, "grant_type": "refresh_token", "refresh_token": rt}).encode()
    req = urllib.request.Request("https://open.tiktokapis.com/v2/oauth/token/", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        js = json.loads(r.read())
    if js.get("refresh_token") and js["refresh_token"] != rt:
        print("注意: TikTokのrefresh_tokenが更新されました。Secretsの TIKTOK_REFRESH_TOKEN を更新してください。")
    return js["access_token"]


def tiktok_upload(video_path, token):
    size = os.path.getsize(video_path)
    body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}}
    req = urllib.request.Request("https://open.tiktokapis.com/v2/post/publish/inbox/video/init/", data=json.dumps(body).encode(),
                                 method="POST", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())["data"]
    with open(video_path, "rb") as f:
        up = urllib.request.Request(d["upload_url"], data=f.read(), method="PUT",
                                    headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size-1}/{size}"})
    with urllib.request.urlopen(up, timeout=300):
        pass
    return d["publish_id"]


def post():
    c = config(); q = load(QUEUE, []); xc = x_creds(); tk = None
    month = now().strftime("%Y-%m")
    x_month = sum(1 for e in q if e["platform"] == "x" and e["status"] == "posted" and e.get("posted_at", "")[:7] == month)
    for e in sorted(q, key=lambda e: e["scheduled_at"]):
        if e["status"] != "approved" or e["scheduled_at"] > now().isoformat():
            continue
        if item(e["item_id"]).get("status") != "on_sale":
            e["status"] = "skipped"; e["error"] = "販売中ではないため投稿しない"; continue
        try:
            if e["platform"] == "x":
                if not xc:
                    e["error"] = "Xの認証情報が未登録"; continue
                if x_month >= c["x_max_per_month"]:
                    e["error"] = "今月のX投稿上限(予算ガード)に達したため保留"; continue
                e["posted_id"] = x_post(e["text"], xc); x_month += 1
            else:
                if tk is None:
                    tk = tiktok_token() or False
                if not tk:
                    e["error"] = "TikTokの認証情報が未登録"; continue
                e["posted_id"] = tiktok_upload(str(ROOT / e["video"]), tk)
                e["note"] = "TikTokアプリの受信箱に下書きとして届きます。24時間以内に投稿してください。"
            e["status"] = "posted"; e["posted_at"] = now().isoformat(timespec="seconds"); e["error"] = None
            log(dict(event="posted", platform=e["platform"], id=e["id"], item_id=e["item_id"], posted_id=e["posted_id"]))
        except urllib.error.HTTPError as err:
            e["attempts"] += 1; e["error"] = f"HTTP {err.code}: {err.read()[:300].decode('utf-8', 'replace')}"
            if e["attempts"] >= c["max_attempts"]:
                e["status"] = "failed"
            log(dict(event="error", platform=e["platform"], id=e["id"], error=e["error"]))
        except Exception as err:
            e["attempts"] += 1; e["error"] = str(err)[:300]
            if e["attempts"] >= c["max_attempts"]:
                e["status"] = "failed"
            log(dict(event="error", platform=e["platform"], id=e["id"], error=e["error"]))
    save(QUEUE, q)


def metrics():
    xc = x_creds()
    if not xc:
        print("Xの認証情報が未登録のため、反応の取得はスキップ"); return
    q = load(QUEUE, [])
    recent = [e for e in q if e["platform"] == "x" and e["status"] == "posted" and e.get("posted_id")
              and e.get("posted_at", "") >= (now() - timedelta(days=7)).isoformat()]
    if not recent:
        return
    data = x_metrics([e["posted_id"] for e in recent[:100]], xc)
    out = ROOT / "metrics" / "x.jsonl"; out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        for d in data:
            f.write(json.dumps(dict(at=now().isoformat(timespec="seconds"), id=d["id"], **d.get("public_metrics", {}),
                                    **{f"np_{k}": v for k, v in (d.get("non_public_metrics") or {}).items()}), ensure_ascii=False) + "\n")


# ---------- 分析 ----------
def mercari_series(iid):
    p = ROOT / "metrics" / "mercari" / f"{iid}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def analyze():
    q = load(QUEUE, [])
    by = {}
    for out in (ROOT / "outputs").glob("m*/script.json"):
        sj = json.loads(out.read_text()); iid = out.parent.name; it = item(iid)
        if "pattern" not in sj:
            continue
        ser = mercari_series(iid)
        likes = [s["num_likes"] for s in ser if s.get("num_likes") is not None]
        bids = [s["total_bids"] for s in ser if s.get("total_bids") is not None]
        posted = any(e["item_id"] == iid and e["status"] == "posted" for e in q)
        r = by.setdefault(sj["pattern"], dict(name=sj.get("pattern_name"), videos=0, posted=0, sold=0, like_gain=0, bids=0))
        r["videos"] += 1; r["posted"] += posted
        r["sold"] += it.get("status") == "sold"
        r["like_gain"] += (likes[-1] - likes[0]) if len(likes) > 1 else 0
        r["bids"] += max(bids) if bids else 0
    weights = {}
    for p, r in by.items():
        if r["posted"] >= 5:   # 投稿5本未満のパターンは判断しない
            weights[p] = round(min(1.5, (r["sold"] + 0.1 * r["like_gain"] + 0.2 * r["bids"]) / r["posted"]), 3)
    save(ROOT / "outputs" / "pattern_scores.json", dict(updated=now().isoformat(timespec="seconds"), by_pattern=by, weights=weights))
    print(json.dumps(by, ensure_ascii=False, indent=1))


# ---------- 管理画面 ----------
def status():
    q = load(QUEUE, []); c = config()
    lines = ["# 古着くん 管理画面", "", f"更新: {now().strftime('%Y-%m-%d %H:%M')}（2時間ごとに自動更新）", ""]
    items = []
    for p in sorted((ROOT / "items").glob("m*/item.json")):
        it = json.loads(p.read_text()); items.append(it)
    on = [i for i in items if i.get("status") == "on_sale"]
    vids = list((ROOT / "outputs").glob("m*/furugikun_*.mp4"))
    cnt = lambda pf, st: sum(1 for e in q if e["platform"] == pf and e["status"] == st)
    lines += ["## 概要", "",
              f"- 取り込み済み商品: {len(items)}件（販売中 {len(on)}件）", f"- 動画: {len(vids)}本",
              f"- TikTok: 承認待ち {cnt('tiktok','awaiting_approval')} / 予定 {cnt('tiktok','approved')} / 送信済み {cnt('tiktok','posted')} / 失敗 {cnt('tiktok','failed')}",
              f"- X: 承認待ち {cnt('x','awaiting_approval')} / 予定 {cnt('x','approved')} / 投稿済み {cnt('x','posted')} / 失敗 {cnt('x','failed')}",
              f"- 自動承認: {'オン' if c['auto_approve'] else 'オフ（承認してから投稿）'}",
              f"- 認証情報: X {'登録済み' if x_creds() else '未登録'} / TikTok {'登録済み' if os.environ.get('TIKTOK_REFRESH_TOKEN') else '未登録'}", ""]
    lines += ["## 販売中の商品", "", "| 商品 | 開始価格 | 現在 | 入札 | いいね | 終了 | 動画・演出 |", "|---|---|---|---|---|---|---|"]
    for it in sorted(on, key=lambda i: i.get("auction_end") or "9"):
        iid = it["item_id"]; sj = ROOT / "outputs" / iid / "script.json"
        pat = json.loads(sj.read_text()).get("pattern_name", "") if sj.exists() else "未作成"
        vid = f"[動画](outputs/{iid}/furugikun_{iid}.mp4)" if (ROOT / "outputs" / iid / f"furugikun_{iid}.mp4").exists() else "—"
        sp = f"¥{it['start_price_yen']:,}" if it.get("start_price_yen") else "取得できず"
        cur = f"¥{it['highest_bid_yen']:,}" if it.get("highest_bid_yen") else f"¥{it.get('price_yen', 0):,}"
        end = (it.get("auction_end") or "")[5:16].replace("T", " ")
        lines.append(f"| [{it['title'][:24]}]({it['url']}) | {sp} | {cur} | {it.get('total_bids', '—')} | {it.get('num_likes', '—')} | {end} | {vid} {pat} |")
    lines += ["", "## 投稿予定（承認待ち・予定）", "", "| ID | 媒体 | 予定日時 | 状態 | 内容 |", "|---|---|---|---|---|"]
    for e in sorted([e for e in q if e["status"] in ("awaiting_approval", "approved")], key=lambda e: e["scheduled_at"])[:40]:
        st = {"awaiting_approval": "承認待ち", "approved": "予定"}[e["status"]]
        lines.append(f"| {e['id']} | {'TikTok' if e['platform']=='tiktok' else 'X'} | {e['scheduled_at'][5:16].replace('T',' ')} | {st} | {e['text'].splitlines()[0][:30]} |")
    lines += ["", "承認するには：アクション →「古着くん動画を作る」→ Run workflow →「承認するID」に ID か all を入れて実行。", ""]
    errs = [e for e in q if e.get("error")]
    lines += ["## エラー・未投稿", ""] + ([f"- {e['id']} {e['platform']} {e['item_id']}: {e['error']}" for e in errs[-20:]] or ["- なし"])
    sc = load(ROOT / "outputs" / "pattern_scores.json", {})
    if sc.get("by_pattern"):
        lines += ["", "## 演出パターン別の成果", "", "| パターン | 動画 | 投稿 | 売れた | いいね増 | 入札 |", "|---|---|---|---|---|---|"]
        for p, r in sc["by_pattern"].items():
            lines.append(f"| {r['name']} | {r['videos']} | {r['posted']} | {r['sold']} | {r['like_gain']} | {r['bids']} |")
    (ROOT / "STATUS.md").write_text("\n".join(lines) + "\n")
    print("STATUS.md を更新")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"plan": plan, "post": post, "metrics": metrics, "analyze": analyze, "status": status}.get(cmd, lambda: None)() \
        if cmd != "approve" else approve(sys.argv[2] if len(sys.argv) > 2 else "all")
