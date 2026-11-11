# 古着くん 各アングルのSVGパーツ。座標系は全アングル共通 viewBox 0 0 400 820。
# 縦の基準線: アホ毛先端≈10 / 頭頂62 / あご242 / 肩248-272 / ジャケット裾470 / 裾折返し712-742 / ブーツ742-798
import re, pathlib

SRC = (pathlib.Path(__file__).parent / 'assets' / 'master_front.svg').read_text()
_svg = re.search(r'<svg[^>]*>(.*)</svg>', SRC, re.S).group(1)
DEFS = re.search(r'<defs>.*?</defs>', _svg, re.S).group(0)
FRONT_BODY = _svg.replace(DEFS, '')  # マスター(正面)そのもの

L = '#2A1E18'
G_OPEN = f'<g stroke="{L}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">'
SHADOW = f'<ellipse cx="200" cy="806" rx="132" ry="11" fill="{L}" opacity="0.12"></ellipse>'


def mirror(s):
    return f'<g transform="translate(400,0) scale(-1,1)">{s}</g>'

# ---------- 共通の小パーツ ----------
def ahoge(d):
    return (f'<path d="{d}" fill="none" stroke="{L}" stroke-width="11"></path>'
            f'<path d="{d}" fill="none" stroke="#3B2A20" stroke-width="5.5"></path>')

AHOGE_FRONT = 'M200 66 C200 50 200 42 200 30 C200 12 226 10 228 26 C229 38 216 42 210 34'
AHOGE_BACK = 'M200 66 C200 50 200 42 200 30 C200 12 174 10 172 26 C171 38 184 42 190 34'
AHOGE_R90 = 'M198 66 C198 50 198 42 199 30 C200 16 208 12 212 18 C215 24 212 30 207 30'
AHOGE_L270 = 'M202 66 C202 50 202 42 202 30 C202 12 216 8 222 20 C228 34 214 40 208 33'
AHOGE_R45 = 'M206 66 C206 50 206 42 206 30 C206 13 224 11 226 25 C227 35 218 39 213 33'
AHOGE_L315 = 'M194 66 C194 50 194 42 194 30 C194 12 222 10 224 26 C225 38 212 42 206 34'

DUCK_STITCH = 'fill="none" stroke="#E3C48E" stroke-width="1.6" stroke-dasharray="4 3"'
DEN_STITCH = 'fill="none" stroke="#D9A54A" stroke-width="1.6" stroke-dasharray="4 3"'
BOOT_STITCH = 'fill="none" stroke="#8A5E20" stroke-width="1.6" stroke-dasharray="3 2.5"'

def cuff(x1, x2):
    return (f'<path d="M{x1} 712 L{x2} 712 L{x2} 742 L{x1} 742 Z" fill="#B7CCDF"></path>'
            f'<path d="M{x1+3} 721 L{x2-3} 721" stroke="#F3EEE4" stroke-width="3"></path>'
            f'<path d="M{x1+3} 725 L{x2-3} 725" stroke="#B5452E" stroke-width="1.6"></path>')

def sole(x, w):
    lugs = ' '.join(f'M{x+12+i*16} 798 L{x+12+i*16} 794' for i in range(int((w-16)//16)+1))
    return (f'<rect x="{x}" y="785" width="{w}" height="13" rx="4" fill="#6B4A2E"></rect>'
            f'<path d="M{x+4} 789 L{x+w-4} 789" fill="none" stroke="#E3C48E" stroke-width="1.4" stroke-dasharray="3 2.5"></path>'
            f'<path d="{lugs}" fill="none" stroke="#4A3220" stroke-width="2"></path>')

def hand(d, thumb=None):
    s = f'<path d="{d}" fill="#F3D2B3"></path>'
    if thumb:
        s += f'<path d="{thumb}" fill="none" stroke-width="2.2"></path>'
    return s

# ---------- 背面 180° ----------
def back():
    s = SHADOW + G_OPEN
    for cx in (160, 240):  # ブーツ(かかと側)
        x1, x2 = cx-36, cx+36
        s += f'<path d="M{x1} 742 L{x2} 742 L{x2+2} 786 L{x1-2} 786 Z" fill="url(#fkSuede)"></path>'
        s += f'<path d="M{x1} 742 L{x2} 742 L{x2} 752 L{x1} 752 Z" fill="#5A3A22" stroke-width="2.5"></path>'
        s += f'<path d="M{cx} 754 L{cx} 784" {BOOT_STITCH}></path>'
        s += f'<path d="M{x1+4} 770 C{cx-16} 764 {cx+16} 764 {x2-4} 770" {BOOT_STITCH}></path>'
        s += sole(x1-6, 84)
    # デニム
    s += '<path d="M114 466 L198 466 L194 742 L126 742 Z" fill="url(#fkDenim)"></path>'
    s += '<path d="M202 466 L286 466 L274 742 L206 742 Z" fill="url(#fkDenim)"></path>'
    s += '<path d="M114 466 L198 466 L194 742 L126 742 Z" fill="url(#fkEdge)" stroke="none"></path>'
    s += '<path d="M202 466 L286 466 L274 742 L206 742 Z" fill="url(#fkEdge)" stroke="none"></path>'
    s += '<ellipse cx="160" cy="540" rx="22" ry="50" fill="url(#fkFade)" stroke="none"></ellipse>'
    s += '<ellipse cx="240" cy="540" rx="22" ry="50" fill="url(#fkFade)" stroke="none"></ellipse>'
    # 膝裏のハチノス(控えめ)
    s += '<path d="M146 636 L174 634 M150 646 L170 645 M226 634 L254 636 M230 645 L250 646" fill="none" stroke="#6E8FB2" stroke-width="1.6"></path>'
    s += f'<path d="M119 472 L129 712 M281 472 L271 712" {DEN_STITCH}></path>'
    s += f'<path d="M196 472 L194 712 M204 472 L206 712" {DEN_STITCH}></path>'
    s += cuff(126, 194) + cuff(206, 274)
    # 袖・手(手の甲側、親指は見えない)
    s += '<path d="M112 272 C98 300 90 360 88 430 L116 434 C118 380 124 330 132 300 Z" fill="url(#fkDuck)"></path>'
    s += '<path d="M288 272 C302 300 310 360 312 430 L284 434 C282 380 276 330 268 300 Z" fill="url(#fkDuck)"></path>'
    s += '<ellipse cx="103" cy="352" rx="7" ry="18" fill="#D2AE80" opacity="0.55" stroke="none"></ellipse>'
    s += '<ellipse cx="297" cy="352" rx="7" ry="18" fill="#D2AE80" opacity="0.55" stroke="none"></ellipse>'
    s += '<path d="M88 424 L116 428 L115 442 L87 438 Z" fill="#8E6338"></path>'
    s += '<path d="M312 424 L284 428 L285 442 L313 438 Z" fill="#8E6338"></path>'
    s += hand('M88 440 C82 452 84 470 96 474 C108 476 116 466 114 450 L114 442 Z')
    s += hand('M312 440 C318 452 316 470 304 474 C292 476 284 466 286 450 L286 442 Z')
    # ジャケット背面(無地・ロゴ/タグなし)
    s += '<path d="M152 248 L112 270 L106 470 L294 470 L288 270 L248 248 Z" fill="url(#fkDuck)"></path>'
    s += '<ellipse cx="226" cy="296" rx="16" ry="10" fill="#C9A272" opacity="0.45" stroke="none"></ellipse>'
    s += f'<path d="M110 460 L290 460" {DUCK_STITCH}></path>'
    s += '<path d="M150 432 C180 440 220 440 250 432 M140 360 C150 366 160 366 168 362" fill="none" stroke="#7A5230" stroke-width="2"></path>'
    s += '<path d="M152 246 C180 238 220 238 248 246 L254 262 C220 254 180 254 146 262 Z" fill="url(#fkCord)"></path>'
    # 頭(後頭部)
    s += '<rect x="186" y="226" width="28" height="28" fill="#E7BC98"></rect>'
    s += '<ellipse cx="116" cy="168" rx="13" ry="16" fill="#F3D2B3"></ellipse>'
    s += '<ellipse cx="284" cy="168" rx="13" ry="16" fill="#F3D2B3"></ellipse>'
    s += '<path d="M112 168 C104 96 148 62 200 62 C252 62 296 96 288 168 C284 200 262 224 238 232 L226 226 L214 234 L200 228 L186 234 L174 226 L162 232 C138 224 116 200 112 168 Z" fill="#3B2A20"></path>'
    s += '<path d="M196 98 C188 104 192 116 202 114 C210 112 210 102 204 100" fill="none" stroke="#5A4334" stroke-width="2.5"></path>'
    s += ahoge(AHOGE_BACK)
    return s + '</g>'

# ---------- 右側面 90°(キャラの右半身が見える/顔は向かって右) ----------
def side_base(pocket=False):
    s = SHADOW + G_OPEN
    # ブーツ(つま先は向かって右)
    s += '<path d="M172 742 L234 742 L238 760 C252 762 262 768 264 778 L264 786 L166 786 L166 752 Z" fill="url(#fkSuede)"></path>'
    s += '<path d="M172 742 L234 742 L236 752 L168 752 Z" fill="#5A3A22" stroke-width="2.5"></path>'
    s += f'<path d="M236 764 C246 762 258 768 262 778" {BOOT_STITCH}></path>'
    s += f'<path d="M170 772 L236 772" {BOOT_STITCH}></path>'
    s += '<path d="M232 754 L244 760 M240 754 L234 762 M238 760 L248 766" fill="none" stroke="#8A5A2A" stroke-width="2.4"></path>'
    s += '<circle cx="236" cy="755" r="2" fill="#D9B46A" stroke-width="1.2"></circle>'
    s += sole(160, 108)
    # デニム(手前脚。外側の縫い目=アウトシームが中央に来る)
    s += '<path d="M152 466 L248 466 L238 742 L170 742 Z" fill="url(#fkDenim)"></path>'
    s += '<path d="M152 466 L248 466 L238 742 L170 742 Z" fill="url(#fkEdge)" stroke="none"></path>'
    s += '<ellipse cx="226" cy="560" rx="16" ry="70" fill="url(#fkFade)" stroke="none"></ellipse>'
    s += '<ellipse cx="222" cy="612" rx="14" ry="16" fill="url(#fkFade)" opacity="0.7" stroke="none"></ellipse>'
    s += '<path d="M226 640 C220 646 214 648 208 648 M180 676 C188 680 196 680 204 676" fill="none" stroke="#6E8FB2" stroke-width="1.6"></path>'
    s += f'<path d="M200 470 L204 712" {DEN_STITCH}></path>'
    s += '<path d="M170 712 L238 712 L238 742 L170 742 Z" fill="#B7CCDF"></path>'
    s += '<path d="M201 712 L201 742 L207 742 L207 712 Z" fill="#F3EEE4" stroke-width="1.5"></path>'
    s += '<path d="M204 713 L204 741" stroke="#B5452E" stroke-width="1.6"></path>'
    # ジャケット側面(前開き。前端からTシャツが細く見える)
    s += '<path d="M244 262 L258 284 L260 470 L246 470 Z" fill="#EFE6D2"></path>'
    s += '<path d="M156 248 L232 248 L250 282 L254 470 L146 470 L150 282 Z" fill="url(#fkDuck)"></path>'
    s += f'<path d="M150 460 L252 460 M246 290 L250 456" {DUCK_STITCH}></path>'
    s += '<path d="M222 396 L250 396 L251 444 L222 444 Z" fill="url(#fkDuck)"></path>'
    s += f'<path d="M225 402 L248 402" {DUCK_STITCH}></path>'
    if pocket:  # キャラ左胸の胸ポケット+ボタン(左側面でのみ見える)
        s += '<path d="M226 316 L248 316 L248 352 L226 352 Z" fill="url(#fkDuck)"></path>'
        s += f'<path d="M229 322 L245 322" {DUCK_STITCH}></path>'
        for y in (332, 374, 416):
            s += f'<circle cx="252" cy="{y}" r="4" fill="#5A3A22" stroke-width="2"></circle>'
    s += '<path d="M206 246 L236 248 L254 290 L240 294 Z" fill="url(#fkCord)"></path>'
    s += '<path d="M156 246 C176 240 196 240 210 244 L214 258 C196 254 176 254 152 262 Z" fill="url(#fkCord)"></path>'
    # 袖(手前の腕)
    s += '<path d="M176 262 C166 300 170 370 176 430 L206 432 C210 370 214 300 210 262 Z" fill="url(#fkDuck)"></path>'
    s += '<ellipse cx="180" cy="352" rx="6" ry="18" fill="#D2AE80" opacity="0.55" stroke="none"></ellipse>'
    s += '<path d="M180 384 C188 388 196 388 204 384" fill="none" stroke="#7A5230" stroke-width="2"></path>'
    s += '<path d="M176 424 L206 426 L206 442 L176 440 Z" fill="#8E6338"></path>'
    s += hand('M178 440 C174 456 178 472 190 474 C202 475 208 464 206 448 L206 442 Z',
              'M204 450 C211 454 209 463 202 463')
    # 頭(横顔。向かって右が顔)
    s += '<rect x="180" y="230" width="32" height="24" fill="#E7BC98"></rect>'
    s += '<path d="M118 160 C118 106 158 78 200 78 C250 78 282 112 282 160 C282 172 284 180 290 188 C292 192 288 194 284 194 C282 214 268 234 240 240 C214 244 190 240 176 232 C140 220 118 196 118 160 Z" fill="#F3D2B3"></path>'
    s += '<path d="M116 166 C104 96 150 62 202 62 C250 62 286 92 284 138 C276 124 266 114 254 110 C246 124 232 128 220 124 C214 132 204 136 196 138 C186 150 180 162 178 176 L170 210 C150 214 128 200 116 166 Z" fill="#3B2A20"></path>'
    s += '<ellipse cx="180" cy="172" rx="12" ry="16" fill="#F3D2B3"></ellipse>'
    s += '<path d="M182 164 C176 168 176 178 184 180" fill="none" stroke-width="2"></path>'
    s += '<path d="M244 140 Q256 134 268 140" fill="none" stroke-width="6"></path>'
    s += '<ellipse cx="258" cy="170" rx="6.5" ry="12.5" fill="#2A1E18" stroke="none"></ellipse>'
    s += '<circle cx="260" cy="164" r="2.8" fill="#FFFFFF" stroke="none"></circle>'
    s += '<ellipse cx="246" cy="196" rx="11" ry="7" fill="#E8957E" opacity="0.45" stroke="none"></ellipse>'
    s += '<path d="M266 206 Q274 214 282 206 Q275 209 266 206 Z" fill="#9C3E32" stroke-width="2.5"></path>'
    s += '<path d="M206 84 C214 78 226 78 234 82" fill="none" stroke="#5A4334" stroke-width="3"></path>'
    return s


def side_r90():
    return side_base(pocket=False) + ahoge(AHOGE_R90) + '</g>'


def side_l270():
    # 左側面:形状は右側面の鏡像。ただし非対称要素(胸ポケット・ボタン・アホ毛・目のハイライト)は描き直す
    base = side_base(pocket=True)
    base = base.replace('<circle cx="260" cy="164" r="2.8" fill="#FFFFFF" stroke="none"></circle>', '')
    hl = '<circle cx="143" cy="164" r="2.8" fill="#FFFFFF" stroke="none"></circle>'
    return mirror(base + '</g>') + G_OPEN + hl + ahoge(AHOGE_L270) + '</g>'

# ---------- 斜め45°(向かって右を向く) ----------
def tq_body(pocket_far=True):
    s = SHADOW + G_OPEN
    # 奥のブーツ → 手前のブーツ(つま先は向かって右下)
    for dx, base in ((92, 0.92), (0, 1.0)):
        x = 124 + dx
        s += f'<path d="M{x+4} 742 L{x+70} 742 L{x+74} 758 C{x+88} 762 {x+96} 770 {x+96} 780 L{x+96} 786 L{x-2} 786 L{x} 752 Z" fill="url(#fkSuede)"></path>'
        s += f'<path d="M{x+4} 742 L{x+70} 742 L{x+71} 752 L{x} 752 Z" fill="#5A3A22" stroke-width="2.5"></path>'
        s += f'<path d="M{x+56} 756 L{x+70} 764 M{x+70} 756 L{x+56} 764 M{x+58} 764 L{x+72} 772" fill="none" stroke="#8A5A2A" stroke-width="2.4"></path>'
        s += f'<circle cx="{x+56}" cy="755" r="2" fill="#D9B46A" stroke-width="1.2"></circle><circle cx="{x+71}" cy="755" r="2" fill="#D9B46A" stroke-width="1.2"></circle>'
        s += f'<path d="M{x+62} 772 C{x+74} 766 {x+88} 770 {x+94} 778" {BOOT_STITCH}></path>'
        s += sole(x-6, 106)
    # デニム(奥脚→手前脚)
    s += '<path d="M204 466 L284 466 L272 742 L212 742 Z" fill="url(#fkDenim)"></path>'
    s += '<path d="M204 466 L284 466 L272 742 L212 742 Z" fill="url(#fkEdge)" stroke="none"></path>'
    s += '<path d="M118 466 L204 466 L198 742 L128 742 Z" fill="url(#fkDenim)"></path>'
    s += '<path d="M118 466 L204 466 L198 742 L128 742 Z" fill="url(#fkEdge)" stroke="none"></path>'
    s += '<ellipse cx="166" cy="566" rx="24" ry="74" fill="url(#fkFade)" stroke="none"></ellipse>'
    s += '<ellipse cx="248" cy="566" rx="20" ry="72" fill="url(#fkFade)" stroke="none"></ellipse>'
    s += '<ellipse cx="166" cy="612" rx="20" ry="16" fill="url(#fkFade)" opacity="0.7" stroke="none"></ellipse>'
    s += '<ellipse cx="246" cy="612" rx="17" ry="15" fill="url(#fkFade)" opacity="0.7" stroke="none"></ellipse>'
    s += '<path d="M188 486 L168 492 M190 498 L172 506 M224 486 L242 492 M222 498 L238 506" fill="none" stroke="#CADBE9" stroke-width="2"></path>'
    s += '<path d="M156 618 C162 621 170 621 176 618 M238 618 C243 621 250 621 255 618" fill="none" stroke="#6E8FB2" stroke-width="1.4" opacity="0.7"></path>'
    s += '<path d="M166 676 C176 680 186 680 194 676 M220 676 C230 680 240 680 248 676" fill="none" stroke="#6E8FB2" stroke-width="2"></path>'
    s += f'<path d="M124 472 L132 712 M279 472 L270 712" {DEN_STITCH}></path>'
    s += cuff(212, 272) + cuff(128, 198)
    # 奥の腕(胴の後ろ)
    s += '<path d="M282 276 C294 300 300 360 302 428 L280 432 C278 380 274 330 270 304 Z" fill="url(#fkDuck)"></path>'
    s += '<path d="M302 422 L280 426 L281 440 L303 436 Z" fill="#8E6338"></path>'
    s += hand('M302 438 C308 452 306 468 296 472 C286 474 278 464 280 450 L281 440 Z')
    # 胴
    s += '<path d="M188 252 L236 252 L234 470 L196 470 Z" fill="#EFE6D2"></path>'
    s += '<path d="M194 254 Q212 268 230 254" fill="none" stroke-width="2.5"></path>'
    s += '<path d="M156 248 L116 272 L110 470 L200 470 L198 306 L184 254 Z" fill="url(#fkDuck)"></path>'
    s += '<path d="M250 250 L282 272 L288 470 L232 470 L232 306 L240 256 Z" fill="url(#fkDuck)"></path>'
    s += '<ellipse cx="146" cy="432" rx="13" ry="8" fill="#C9A272" opacity="0.5" stroke="none"></ellipse>'
    s += f'<path d="M114 460 L198 460 M234 460 L286 460 M194 308 L196 456 M236 308 L235 456 M124 282 L118 456" {DUCK_STITCH}></path>'
    s += '<path d="M134 344 C146 354 156 356 166 352" fill="none" stroke="#7A5230" stroke-width="2"></path>'
    s += '<path d="M124 396 L180 396 L180 444 L124 444 Z" fill="url(#fkDuck)"></path>'
    s += '<path d="M246 396 L282 396 L283 444 L246 444 Z" fill="url(#fkDuck)"></path>'
    s += f'<path d="M128 402 L176 402 M249 402 L279 402" {DUCK_STITCH}></path>'
    if pocket_far:
        s += '<path d="M248 316 L278 316 L279 352 L248 352 Z" fill="url(#fkDuck)"></path>'
        s += f'<path d="M251 322 L276 322" {DUCK_STITCH}></path>'
        for y in (332, 374, 416):
            s += f'<circle cx="238" cy="{y}" r="4.3" fill="#5A3A22" stroke-width="2"></circle>'
    s += '<path d="M156 246 L182 250 L202 304 L182 300 L142 262 Z" fill="url(#fkCord)"></path>'
    s += '<path d="M250 248 L238 252 L228 304 L242 300 L268 264 Z" fill="url(#fkCord)"></path>'
    # 手前の腕
    s += '<path d="M118 274 C104 300 96 360 94 430 L122 434 C124 380 130 330 138 300 Z" fill="url(#fkDuck)"></path>'
    s += '<ellipse cx="109" cy="352" rx="7" ry="18" fill="#D2AE80" opacity="0.55" stroke="none"></ellipse>'
    s += '<path d="M94 424 L122 428 L121 442 L93 438 Z" fill="#8E6338"></path>'
    s += hand('M94 440 C88 452 90 470 102 474 C114 476 122 466 120 450 L120 442 Z',
              'M118 452 C124 456 123 464 116 465')
    return s


def tq_head_r45():
    s = '<rect x="190" y="232" width="28" height="22" fill="#E7BC98"></rect>'
    s += '<ellipse cx="202" cy="160" rx="84" ry="82" fill="#F3D2B3"></ellipse>'
    s += '<path d="M118 178 C104 100 150 62 206 62 C258 62 292 100 284 158 C280 136 270 122 258 116 C248 128 228 132 208 124 C190 132 168 138 150 150 C144 160 142 170 142 182 C132 188 122 186 118 178 Z" fill="#3B2A20"></path>'
    s += '<ellipse cx="138" cy="172" rx="11" ry="15" fill="#F3D2B3"></ellipse>'
    s += '<path d="M140 164 C134 168 134 178 141 180" fill="none" stroke-width="2"></path>'
    s += '<path d="M168 84 C180 76 194 74 204 76" fill="none" stroke="#5A4334" stroke-width="3"></path>'
    s += '<path d="M174 142 Q190 134 204 140 M236 140 Q248 134 260 142" fill="none" stroke-width="6"></path>'
    s += '<ellipse cx="190" cy="170" rx="9" ry="13" fill="#2A1E18" stroke="none"></ellipse>'
    s += '<ellipse cx="250" cy="170" rx="7" ry="12.5" fill="#2A1E18" stroke="none"></ellipse>'
    s += '<circle cx="193" cy="164" r="3.2" fill="#FFFFFF" stroke="none"></circle>'
    s += '<circle cx="252" cy="164" r="2.8" fill="#FFFFFF" stroke="none"></circle>'
    s += '<ellipse cx="168" cy="196" rx="13" ry="7" fill="#E8957E" opacity="0.45" stroke="none"></ellipse>'
    s += '<ellipse cx="262" cy="196" rx="9" ry="6" fill="#E8957E" opacity="0.45" stroke="none"></ellipse>'
    s += '<path d="M232 186 Q238 191 244 186" fill="none" stroke-width="2.5"></path>'
    s += '<path d="M216 206 Q230 222 246 205 Q230 211 216 206 Z" fill="#9C3E32" stroke-width="2.5"></path>'
    s += ahoge(AHOGE_R45)
    return s


def tq_head_l315():
    s = '<rect x="182" y="232" width="28" height="22" fill="#E7BC98"></rect>'
    s += '<ellipse cx="198" cy="160" rx="84" ry="82" fill="#F3D2B3"></ellipse>'
    s += '<path d="M282 178 C296 100 250 62 194 62 C142 62 106 100 116 160 C122 144 136 132 152 126 C168 134 192 132 208 122 C220 114 236 116 248 126 C254 140 258 160 258 182 C268 188 278 186 282 178 Z" fill="#3B2A20"></path>'
    s += '<ellipse cx="262" cy="172" rx="11" ry="15" fill="#F3D2B3"></ellipse>'
    s += '<path d="M260 164 C266 168 266 178 259 180" fill="none" stroke-width="2"></path>'
    s += '<path d="M206 76 C218 74 230 78 238 84" fill="none" stroke="#5A4334" stroke-width="3"></path>'
    s += '<path d="M140 142 Q152 134 164 140 M196 140 Q210 134 226 142" fill="none" stroke-width="6"></path>'
    s += '<ellipse cx="150" cy="170" rx="7" ry="12.5" fill="#2A1E18" stroke="none"></ellipse>'
    s += '<ellipse cx="210" cy="170" rx="9" ry="13" fill="#2A1E18" stroke="none"></ellipse>'
    s += '<circle cx="152" cy="164" r="2.8" fill="#FFFFFF" stroke="none"></circle>'
    s += '<circle cx="213" cy="164" r="3.2" fill="#FFFFFF" stroke="none"></circle>'
    s += '<ellipse cx="138" cy="196" rx="9" ry="6" fill="#E8957E" opacity="0.45" stroke="none"></ellipse>'
    s += '<ellipse cx="232" cy="196" rx="13" ry="7" fill="#E8957E" opacity="0.45" stroke="none"></ellipse>'
    s += '<path d="M156 186 Q162 191 168 186" fill="none" stroke-width="2.5"></path>'
    s += '<path d="M154 205 Q170 222 184 206 Q170 211 154 205 Z" fill="#9C3E32" stroke-width="2.5"></path>'
    s += ahoge(AHOGE_L315)
    return s


def tq_r45():
    return tq_body(True) + tq_head_r45() + '</g>'


def tq_l315():
    # 体は45°の鏡像(非対称要素=胸ポケット・ボタンは外して描き直し)、頭は描き直し
    body = mirror(tq_body(False) + '</g>')
    s2 = G_OPEN
    for y in (332, 374, 416):
        s2 += f'<circle cx="208" cy="{y}" r="4.5" fill="#5A3A22" stroke-width="2"></circle>'
    # 315°は手前がキャラの左半身。ボタンは手前パネルの前端、胸ポケットは奥側(向かって左)ではなく手前側にある
    pocket = G_OPEN + '<path d="M222 316 L262 316 L262 352 L222 352 Z" fill="url(#fkDuck)"></path>' + f'<path d="M226 322 L258 322" {DUCK_STITCH}></path>' + '</g>'
    return body + s2 + '</g>' + pocket + G_OPEN + tq_head_l315() + '</g>'


def front():
    return FRONT_BODY

# ---------- 表情(正面の頭部のみ差し替え) ----------
FACE_BASE = ('<rect x="186" y="232" width="28" height="22" fill="#E7BC98"></rect>'
             '<ellipse cx="116" cy="168" rx="13" ry="16" fill="#F3D2B3"></ellipse>'
             '<ellipse cx="284" cy="168" rx="13" ry="16" fill="#F3D2B3"></ellipse>'
             '<ellipse cx="200" cy="160" rx="86" ry="82" fill="#F3D2B3"></ellipse>'
             '<path d="M114 162 C106 96 148 62 200 62 C254 62 296 96 286 162 C280 138 266 122 246 116 C236 130 210 134 188 124 C172 134 146 138 124 150 Z" fill="#3B2A20"></path>'
             '<path d="M160 84 C172 76 186 74 196 76" fill="none" stroke="#5A4334" stroke-width="3"></path>')

def eyes(rx=9, ry=13, dy=0):
    return (f'<ellipse cx="168" cy="{170+dy}" rx="{rx}" ry="{ry}" fill="#2A1E18" stroke="none"></ellipse>'
            f'<ellipse cx="232" cy="{170+dy}" rx="{rx}" ry="{ry}" fill="#2A1E18" stroke="none"></ellipse>'
            f'<circle cx="171" cy="{164+dy-(ry-13)*0.5}" r="3.2" fill="#FFFFFF" stroke="none"></circle>'
            f'<circle cx="235" cy="{164+dy-(ry-13)*0.5}" r="3.2" fill="#FFFFFF" stroke="none"></circle>')

def cheeks(op=0.45):
    return (f'<ellipse cx="146" cy="196" rx="13" ry="7" fill="#E8957E" opacity="{op}" stroke="none"></ellipse>'
            f'<ellipse cx="254" cy="196" rx="13" ry="7" fill="#E8957E" opacity="{op}" stroke="none"></ellipse>')

NOSE = '<path d="M196 188 Q200 192 204 188" fill="none" stroke-width="2.5"></path>'
BROWS_N = '<path d="M150 140 Q166 132 182 138 M218 138 Q234 132 250 140" fill="none" stroke-width="6"></path>'
MOUTH_N = '<path d="M184 206 Q200 224 216 206 Q200 212 184 206 Z" fill="#9C3E32" stroke-width="2.5"></path>'

EXPR = {
    '通常': BROWS_N + eyes() + cheeks() + NOSE + MOUTH_N + ahoge(AHOGE_FRONT),
    '笑顔': ('<path d="M150 136 Q166 128 182 134 M218 134 Q234 128 250 136" fill="none" stroke-width="6"></path>'
            '<path d="M157 174 Q168 160 179 174 M221 174 Q232 160 243 174" fill="none" stroke-width="5"></path>'
            + cheeks(0.65) + NOSE +
            '<path d="M178 202 Q200 234 222 202 Q200 210 178 202 Z" fill="#9C3E32" stroke-width="2.5"></path>'
            '<path d="M190 218 Q200 224 210 218 Q200 214 190 218 Z" fill="#D9786A" stroke="none"></path>'
            + ahoge(AHOGE_FRONT)),
    '驚き': ('<path d="M150 128 Q166 118 182 126 M218 126 Q234 118 250 128" fill="none" stroke-width="6"></path>'
            + eyes(10, 15) + cheeks(0.35) + NOSE +
            '<ellipse cx="200" cy="212" rx="8" ry="10" fill="#9C3E32" stroke-width="2.5"></ellipse>'
            + ahoge('M200 66 C200 44 200 24 201 8 C202 -4 214 -6 214 4 C214 10 208 12 205 8')),
    '困り顔': ('<path d="M152 142 Q166 138 182 130 M218 130 Q234 138 248 142" fill="none" stroke-width="6"></path>'
             + eyes(8.5, 11.5, 2) + cheeks(0.35) + NOSE +
             '<path d="M186 210 Q193 205 200 210 Q207 215 214 210" fill="none" stroke-width="3"></path>'
             '<path d="M264 128 C258 140 258 148 264 150 C270 148 270 140 264 128 Z" fill="#CFE3F0" stroke-width="2"></path>'
             + ahoge('M200 66 C200 58 203 50 212 47 C224 44 232 52 230 62 C229 68 222 70 219 64')),
    '真剣な表情': ('<path d="M152 134 L182 142 M218 142 L248 134" fill="none" stroke-width="6.5"></path>'
              + eyes(8.5, 11, 2) +
              '<path d="M158 162 L178 163 M222 163 L242 162" fill="none" stroke-width="3"></path>'
              + cheeks(0.3) + NOSE +
              '<path d="M188 210 L212 210" fill="none" stroke-width="3"></path>'
              + ahoge(AHOGE_FRONT)),
    '自信のある表情': ('<path d="M150 136 Q166 126 182 134 M218 140 Q234 136 250 140" fill="none" stroke-width="6"></path>'
                + eyes(9, 12, 1) +
                '<path d="M157 162 Q168 158 179 162 M221 164 Q232 160 243 164" fill="none" stroke-width="3.5"></path>'
                + cheeks(0.45) + NOSE +
                '<path d="M184 204 Q204 220 220 200 Q206 210 184 204 Z" fill="#9C3E32" stroke-width="2.5"></path>'
                + ahoge(AHOGE_FRONT)),
}

def expr_head(name):
    return G_OPEN + FACE_BASE + EXPR[name] + '</g>'

# 正面顔/斜め顔/横顔(頭部のみ切り出しはviewBoxで行う)
VIEWS = {
    '正面 0°': front,
    '右斜め 45°': tq_r45,
    '右側面 90°': side_r90,
    '背面 180°': back,
    '左側面 270°': side_l270,
    '左斜め 315°': tq_l315,
}

# 手(開いた手・商品を持つ手)— 本資料で初めて定義
def hand_open():
    return (G_OPEN +
            '<path d="M60 112 C52 82 56 60 70 52 L130 52 C144 60 148 82 140 112 C136 132 120 144 100 144 C80 144 64 132 60 112 Z" fill="#F3D2B3"></path>'
            '<rect x="62" y="6" width="17" height="56" rx="8.5" fill="#F3D2B3"></rect>'
            '<rect x="82" y="0" width="17" height="60" rx="8.5" fill="#F3D2B3"></rect>'
            '<rect x="102" y="2" width="17" height="58" rx="8.5" fill="#F3D2B3"></rect>'
            '<rect x="122" y="12" width="15" height="50" rx="7.5" fill="#F3D2B3"></rect>'
            '<path d="M60 100 C44 92 30 76 30 64 C30 56 40 54 46 60 L66 82" fill="#F3D2B3"></path>'
            '<path d="M64 52 L136 52" fill="none" stroke="#F3D2B3" stroke-width="6"></path>'
            '<path d="M80 104 C92 112 108 112 120 104" fill="none" stroke="#E0B08E" stroke-width="2"></path>'
            '<path d="M58 140 L142 140 L144 168 L56 168 Z" fill="#8E6338"></path>'
            '</g>')

def hand_hold():
    # ハンガーのバーを握る手(親指は手前、4本指が奥に回り込む)
    return (G_OPEN +
            '<path d="M10 70 L190 70" fill="none" stroke="#8C8C8C" stroke-width="8"></path>'
            '<path d="M10 70 L190 70" fill="none" stroke="#B9B9B9" stroke-width="3"></path>'
            '<path d="M64 40 C60 20 76 10 100 10 C126 10 142 22 138 44 L136 98 C134 116 118 126 100 126 C80 126 66 116 64 98 Z" fill="#F3D2B3"></path>'
            '<path d="M72 58 C86 62 118 62 132 58 M72 80 C86 84 118 84 132 80" fill="none" stroke-width="2.2"></path>'
            '<path d="M90 50 C88 60 88 70 92 78 M112 50 C110 60 110 70 114 78" fill="none" stroke-width="2"></path>'
            '<path d="M66 64 C54 64 48 74 52 84 C56 92 68 92 76 86" fill="#F3D2B3"></path>'
            '<path d="M62 118 L138 118 L140 146 L60 146 Z" fill="#8E6338"></path>'
            '</g>')
