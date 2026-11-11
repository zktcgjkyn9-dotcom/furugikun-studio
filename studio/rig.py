# 古着くん 関節リグ(正面)。デザインはマスターと同一。腕は肩・肘・手首で回転、手は4ポーズ。
import sys, re, math
sys.path.insert(0, __import__('os').path.dirname(__file__))
import views as V

FB = V.FRONT_BODY
def section(a, b):
    return FB.split(a)[1].split(b)[0]
LEGS = section('<!-- boots -->', '<!-- tee -->')
TEE = section('<!-- tee -->', '<!-- sleeves + hands -->')
JACKET = section('<!-- jacket body -->', '<!-- neck + head -->')
NECK = '<rect x="186" y="232" width="28" height="22" fill="#E7BC98"></rect>'
FACE_BASE = V.FACE_BASE.replace(NECK, '')
G = V.G_OPEN
SKIN = '#F3D2B3'

# ---- 腕(ローカル座標:肩=原点、下向きが+y) ----
UPPER = ('<path d="M-15 -4 C-17 26 -16 56 -14 82 L14 82 C16 56 17 26 15 -4 C12 -16 -12 -16 -15 -4 Z" fill="url(#fkDuck)"></path>'
         '<ellipse cx="-6" cy="66" rx="5" ry="12" fill="#D2AE80" opacity="0.55" stroke="none"></ellipse>')
FORE = ('<path d="M-14 2 C-12 -12 12 -12 14 2 L13 64 L-13 64 Z" fill="url(#fkDuck)"></path>'
        '<path d="M-8 30 C-3 33 3 33 8 30" fill="none" stroke="#7A5230" stroke-width="2"></path>'
        '<path d="M-13.5 62 L13.5 62 L14 76 L-14 76 Z" fill="#8E6338"></path>')

def finger(x, y, w, h, rot=0, cx=None, cy=None):
    t = f' transform="rotate({rot} {cx} {cy})"' if rot else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w/2}" fill="{SKIN}" stroke-width="2.2"{t}></rect>'

HANDS = {
    # 自然に下ろした手(マスターと同形)
    'rest': ('<path d="M-13 0 C-19 12 -17 30 -4 34 C8 36 15 26 13 10 L13 0 Z" fill="#F3D2B3"></path>'
             '<path d="M11 10 C17 14 16 22 9 23" fill="none" stroke-width="2.2"></path>'),
    # 開いた手:指5本(4本+親指)
    'open': (finger(-12.5, 14, 6.4, 17) + finger(-5.6, 16, 6.4, 20) + finger(1.2, 16, 6.4, 19) + finger(7.8, 14, 6, 15)
             + finger(9, 0, 6.4, 17, -50, 12, 4)
             + '<ellipse cx="-0.5" cy="12" rx="13.5" ry="12.5" fill="#F3D2B3" stroke-width="2.2"></ellipse>'
             + '<path d="M-6 13 C-2 16 3 16 6 13" fill="none" stroke="#E0B08E" stroke-width="1.6"></path>'),
    # 指差し:人差し指を伸ばす
    'point': (finger(-1, 16, 7, 24)
              + '<path d="M-12 2 C-16 12 -14 25 -3 27 C8 28 13 21 12 8 L12 2 Z" fill="#F3D2B3"></path>'
              + '<path d="M-10 18 C-7 22 -3 23 0 21" fill="none" stroke-width="1.8"></path>'
              + '<path d="M10 9 C16 13 15 20 8 21" fill="none" stroke-width="2.2"></path>'),
    # 親指を立てる:親指は前腕と同じ向きに伸びる
    'thumb': ('<path d="M-12 0 C-15 8 -14 22 -4 24 C7 25 12 18 12 8 L12 0 Z" fill="#F3D2B3"></path>'
              '<path d="M-11 9 L3 9 M-11 15 L3 15" fill="none" stroke-width="1.8"></path>'
              + finger(3, 10, 9, 27)
              + '<path d="M5 16 L10 16" fill="none" stroke-width="1.6"></path>'),
}

def arm(px, py, up, fore, hand_ang, pose, mirror=False):
    m = ' scale(-1 1)' if mirror else ''
    return (f'<g transform="translate({px} {py}){m} rotate({up:.2f})">{UPPER}'
            f'<g transform="translate(0 80) rotate({fore:.2f})">{FORE}'
            f'<g transform="translate(0 74) rotate({hand_ang:.2f}) scale({1.0 if pose == "rest" else 1.22})">{HANDS[pose]}</g></g></g>')

AHOGE_RE = re.compile(r'(<path d="M200 66 [^"]*" fill="none" stroke="#2A1E18" stroke-width="11"></path><path d="M200 66 [^"]*" fill="none" stroke="#3B2A20" stroke-width="5.5"></path>)')

def face(expr, t, talking, blink, dx, ahoge_ang):
    feats = V.EXPR[expr]
    ah = AHOGE_RE.search(feats).group(1)
    feats = feats.replace(ah, '')
    if blink and expr != '笑顔':
        feats = re.sub(r'<ellipse cx="(168|232)" cy="(\d+)" rx="[\d.]+" ry="[\d.]+" fill="#2A1E18" stroke="none"></ellipse>',
                       lambda mm: f'<path d="M{int(mm.group(1))-10} {mm.group(2)} Q{mm.group(1)} {int(mm.group(2))+3} {int(mm.group(1))+10} {mm.group(2)}" fill="none" stroke-width="4"></path>', feats)
        feats = re.sub(r'<circle cx="(171|235)"[^>]*fill="#FFFFFF"[^>]*></circle>', '', feats)
    if talking == 'closed' and expr != '驚き':
        feats = re.sub(r'<path d="M1[78]\d 20\d Q[^"]*Z" fill="#9C3E32"[^>]*></path>', '<path d="M186 208 Q200 214 214 208" fill="none" stroke-width="3"></path>', feats)
        feats = re.sub(r'<path d="M190 218 Q200 224[^>]*></path>', '', feats)
    return (G + FACE_BASE + f'<g transform="translate({dx:.2f} 0)">{feats}</g>'
            + f'<g transform="rotate({ahoge_ang:.2f} 200 66)">{ah}</g></g>')

def character(st):
    """st: dict of pose parameters"""
    hop = st.get('hop', 0)
    sway = st.get('sway', 0); shift = st.get('shift', 0); lean = st.get('lean', 1)
    up_body = (f'<g transform="translate({200+shift:.2f} 470) rotate({sway:.2f}) scale({lean:.3f}) translate(-200 -470)">'
               + G + NECK + TEE + JACKET + '</g>'
               + G + arm(124, 282, st['L_up'], st['L_fore'], st['L_hand'], st['L_pose'])
               + arm(276, 282, st['R_up'], st['R_fore'], st['R_hand'], st['R_pose'], mirror=True) + '</g>'
               + f'<g transform="translate(0 {st.get("nod", 0):.2f}) rotate({st.get("tilt", 0):.2f} 200 240)">'
               + face(st['expr'], st['t'], st['mouth'], st['blink'], st.get('look', 0), st.get('ahoge', 0)) + '</g>'
               + '</g>')
    return (V.SHADOW + f'<g transform="translate(0 {-hop:.2f})">' + G + LEGS + '</g>' + up_body + '</g>')
