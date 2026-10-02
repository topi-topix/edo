#!/usr/bin/env python3
"""表店の暖簾・看板を店ごとに焼き分ける(EDO-0503)。

在庫の表店 shop01・shop02(edogoyomi)は 1 枚の画像を UV で割った作りで、暖簾と看板もその中の
決まった四角に描いてある(「呉服太物 川田屋」◇に十)。その四角だけを店ごとに塗り替えた画像を
`Assets/Edo/Textures/Noren/<shop>_<key>.jpg` へ書く。どの店をどう染めるかの正典は
`docs/Sashizu/noren.json`(屋号・業種・暖簾の色・印・文字・典拠と確度)。

    python3 Tools/Unity/bake_noren.py            # 全部焼く
    python3 Tools/Unity/bake_noren.py --sheet    # 確かめ用の一覧 PNG も書く(scratchpad へ)

⛔ 元の画像(Assets/edogoyomi/…)は在庫のパックで gitignore。書き換えない。
"""
import argparse, json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPEC = os.path.join(ROOT, "docs/Sashizu/noren.json")
OUT = os.path.join(ROOT, "Assets/Edo/Textures/Noren")
FONT = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"

# 元の画像と、塗り替える四角(画素・x0,y0,x1,y1)。四角は画像を開いて実測した(2026-10-01)。
SHOPS = {
    "shop01": {
        "src": "Assets/edogoyomi/es_shop01/shop01.jpg",
        "boxes": [("plain", (876, 993, 981, 1093)),        # 無地の暖簾(短い)
                  ("crest", (1002, 1264, 1155, 1417))],    # 紋を染め抜いた暖簾
    },
    "shop02": {
        "src": "Assets/edogoyomi/es_shop02/shop02.jpg",
        "boxes": [("plain", (324, 1073, 418, 1167)),       # 半暖簾の無地
                  ("crest", (427, 1076, 522, 1168)),       # 半暖簾の紋
                  ("plain", (557, 1015, 677, 1250)),       # 長暖簾の無地
                  ("text", (692, 1015, 812, 1250)),        # 長暖簾の屋号と商い
                  ("kanban", (947, 1323, 1017, 1455)),     # 置き看板の板面(白)
                  ("kanban", (1065, 1323, 1135, 1455))],
    },
}


def font(px):
    return ImageFont.truetype(FONT, int(px), index=2)   # W6


def cloth(img, box, rgb):
    """四角を rgb の布に染め直す。元の布目(明るさの揺れ)は残す。"""
    x0, y0, x1, y1 = box
    g = img.crop(box).convert("L")
    reg = np.asarray(g).astype(float)
    # 元の染め抜き(白い字・紋)は布目ではないので消す: 明るい画素を太らせた跡を布の中央値で埋める
    base = float(np.median(reg))
    ink = np.asarray(Image.fromarray(((reg > base * 1.35) * 255).astype(np.uint8))
                     .filter(ImageFilter.MaxFilter(7))) > 0
    reg = np.where(ink, base, reg)
    lum = reg / max(1.0, base)                             # 中央値 1 の布目
    lum = np.clip(0.85 + (lum - 1.0) * 0.6, 0.6, 1.2)      # 揺れを弱めて残す
    out = np.stack([np.clip(lum * c, 0, 255) for c in rgb], -1).astype(np.uint8)
    img.paste(Image.fromarray(out, "RGB"), (x0, y0))


def ink_for(rgb):
    """布の色に対する染め抜き(白)か墨(濃)か。"""
    y = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return (238, 234, 222) if y < 140 else (40, 30, 24)


def draw_mark(d, cx, cy, r, mark, ch, ink, width):
    """印(屋号の印)。mark: hishi / maru / yama / kaku / igeta / none。ch は中の一字。"""
    w = max(2, int(width))
    if mark == "hishi":
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], outline=ink, width=w)
    elif mark == "maru":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=w)
    elif mark == "kaku":
        k = r * 0.8
        d.rectangle([cx - k, cy - k, cx + k, cy + k], outline=ink, width=w)
    elif mark == "yama":
        d.line([(cx - r, cy - r * 0.35), (cx, cy - r), (cx + r, cy - r * 0.35)], fill=ink, width=w)
    elif mark == "igeta":
        k = r * 0.75
        for s in (-0.35, 0.35):
            d.line([(cx + s * r, cy - k), (cx + s * r, cy + k)], fill=ink, width=w)
            d.line([(cx - k, cy + s * r), (cx + k, cy + s * r)], fill=ink, width=w)
    if ch:
        f = font(r * (0.95 if mark in ("maru", "hishi", "kaku") else 1.1))
        dy = r * 0.25 if mark == "yama" else 0
        d.text((cx, cy + dy), ch, font=f, fill=ink, anchor="mm")


def vtext(d, x, y0, y1, text, ink, maxpx):
    """縦書き 1 行を x の芯に、y0..y1 へ均して置く。"""
    n = len(text)
    if n == 0:
        return
    px = min(maxpx, (y1 - y0) / n * 0.92)
    f = font(px)
    step = (y1 - y0) / n
    for i, c in enumerate(text):
        d.text((x, y0 + step * (i + 0.5)), c, font=f, fill=ink, anchor="mm")


def bake(shop, v):
    sp = SHOPS[shop]
    img = Image.open(os.path.join(ROOT, sp["src"])).convert("RGB")
    rgb = tuple(v["color"])
    ink = ink_for(rgb)
    for role, box in sp["boxes"]:
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        if role == "kanban":
            # 板面は白木の白のまま、墨で商いと印。
            d = ImageDraw.Draw(img)
            d.rectangle(box, fill=(236, 232, 220))
            words = v.get("kanban") or v.get("trade_text", "")
            cols = words.split("/") if "/" in words else [words]
            top = y0 + h * 0.06; bot = y0 + h * 0.62
            for i, col in enumerate(cols[:2]):
                cx = x1 - w * (0.30 + 0.40 * i) if len(cols) > 1 else x0 + w / 2
                vtext(d, cx, top, bot, col, (34, 26, 20), w * 0.38)
            draw_mark(d, x0 + w / 2, y0 + h * 0.80, min(w, h) * 0.20, v.get("mark", "none"),
                      v.get("mark_char", ""), (34, 26, 20), w * 0.05)
            continue
        cloth(img, box, rgb)
        d = ImageDraw.Draw(img)
        if role == "crest":
            draw_mark(d, x0 + w / 2, y0 + h / 2, min(w, h) * 0.33, v.get("mark", "none"),
                      v.get("mark_char", ""), ink, min(w, h) * 0.05)
        elif role == "text":
            # 屋号を芯に大きく、商いを右上に小さく(元の「呉服 太物 / 川田屋」の割付に倣う)
            yago = v.get("yago", "")
            vtext(d, x0 + w * 0.42, y0 + h * 0.10, y0 + h * 0.58, yago, ink, w * 0.30)
            tt = v.get("trade_text", "")
            if tt:
                cols = tt.split("/")
                for i, col in enumerate(cols[:2]):
                    vtext(d, x0 + w * (0.82 - 0.0 * i) if i == 0 else x0 + w * 0.14,
                          y0 + h * 0.08, y0 + h * 0.08 + min(len(col), 3) * w * 0.17, col, ink, w * 0.16)
            draw_mark(d, x0 + w * 0.5, y0 + h * 0.77, w * 0.20, v.get("mark", "none"),
                      v.get("mark_char", ""), ink, w * 0.035)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", help="確かめ用の一覧 PNG の書き先")
    a = ap.parse_args()
    spec = json.load(open(SPEC, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    thumbs = []
    for v in spec["variants"]:
        for shop in ("shop01", "shop02"):
            img = bake(shop, v)
            p = os.path.join(OUT, "%s_%s.jpg" % (shop, v["key"]))
            img.save(p, quality=88)
            if shop == "shop02":
                thumbs.append((v["key"], img.crop((300, 1000, 1180, 1500)).resize((440, 250))))
            if shop == "shop01":
                thumbs.append((v["key"] + "/01", img.crop((850, 980, 1180, 1430)).resize((165, 225))))
        print("焼いた:", v["key"], v.get("yago", ""), v.get("trade", ""))
    if a.sheet:
        cols = 4
        cw, ch = 460, 270
        sheet = Image.new("RGB", (cols * cw, ((len(thumbs) + cols - 1) // cols) * ch), (250, 250, 250))
        d = ImageDraw.Draw(sheet)
        for i, (k, t) in enumerate(thumbs):
            x, y = (i % cols) * cw, (i // cols) * ch
            sheet.paste(t, (x + 10, y + 16))
            d.text((x + 10, y + 1), k, fill=(0, 0, 0), font=font(13))
        sheet.save(a.sheet)
        print("一覧:", a.sheet)


if __name__ == "__main__":
    sys.exit(main())
