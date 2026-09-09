# -*- coding: utf-8 -*-
"""検証レンダの**測色** — 庭方・考証方と**同じ物差し**で明度と色相を測る。

    python3 Tools/Blender/check_color.py --preset shaden
    python3 Tools/Blender/check_color.py <png> 名前=x0,y0,x1,y1 [...]   # 0..1 の比で指定

━━━ なぜ道具にするか ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
庭方19巡目 指3 / 考証20巡目 高3 は **どちらも「基壇が暗すぎる」**という同じ判定を、
`Screenshots/sanno_shaden_koshi_near.png` の **RGB中央値と H/S/V** で出した:

    基壇 上段(陽) (53,55,54) H180 S6.0 V21.6 / 高欄 笠木 (110,97,93) H15 S14.6 V43.1

⛔ **部材方がこれを目で見て「明るくした」と言っても、輪は閉じない。**
  受入値(V 52〜60% など)は数なので、**数で測って返す**まで未検査(規則19)。
⇒ `--preset shaden` の矩形は**カメラが固定**の `shots()` に対して決め打ちしてある。
  ⚠ カメラ(`build_sanno_shaden.shots`)を動かしたら矩形も選び直すこと。
  ⚠ 矩形は **0..1 の比**で持つ(解像度を変えても同じ所を測る)。

【明度の階段】庭方の設計: **白洲(明るい砂)→ 基壇 → 木部 → 銅瓦** の順に暗くなる。
  ⇒ この道具は V を並べ、**順序が崩れていたら ⛔ を刷る**。
"""
import sys, os, colorsys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SHOT = os.path.join(REPO, "Screenshots")

# ⚠ 比(x0, y0, x1, y1)。原点は画像の左上。カメラは `build_sanno_shaden.shots` が固定。
PRESET = {
    "shaden": [
        # (画像, 部位, 矩形)
        # ⚠ **上段は縁の陰に入る**(縁は 0.90m 持ち出し、上段はバッターで 0.08 引っ込む)。
        #   ⇒ 同じ材でも 上段と下段で **15ポイント**開く。⛔ 片方だけ測って合否にしない。
        ("sanno_shaden_koshi_near.png", "基壇 上段(縁の陰)", (0.60, 0.600, 0.74, 0.640)),
        ("sanno_shaden_koshi_near.png", "基壇 下段(陽)",     (0.60, 0.660, 0.74, 0.705)),
        ("sanno_shaden_koshi_near.png", "高欄 笠木(木部)", (0.42, 0.360, 0.72, 0.378)),
        ("sanno_shaden_koshi_near.png", "壁 縦板",          (0.70, 0.055, 0.80, 0.170)),
        ("sanno_shaden_koshi_near.png", "白洲(地面・陽)",  (0.04, 0.560, 0.20, 0.700)),
        ("sanno_shaden_south_elev.png", "銅瓦(大屋根)",    (0.26, 0.360, 0.36, 0.395)),
    ],
}

# ⭐ 明度の階段(庭方19巡目 指3)。⛔ 名前の羅列ではなく **この順で V が下がる**ことを検める。
# ⛔⛔ **画像を跨いで明度を比べない。**`V.studio` の灯は同じでも、面の向き・陰・画角が違う。
#   ⇒ 階段は **同じ1枚(`koshi_near`)の中**で見える3つだけで検める。
#   ⚠ 銅瓦は `koshi_near` に写らないので階段には入れない — **別画像の参考値**として刷るだけ。
#     (実測では銅瓦 62.4% > 木部 43.9% で、庭方の「木部 → 銅瓦」の段は**下がっていない**。
#      ⛔ 屋根は触るなと言われているので、これは庭方へ返す所見。)
LADDER = ["白洲(地面・陽)", "基壇 下段(陽)", "壁 縦板"]

# ⭐ 受入値(庭方19巡目 指3)。⛔ ここを部材方が動かさない — 動かすのは庭方。
ACCEPT = {
    "基壇 下段(陽)": dict(h=(25.0, 50.0), s=(0.0, 8.0), v=(52.0, 60.0)),
}


def median(xs):
    ys = sorted(xs)
    n = len(ys)
    return ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2.0


def sample(path, box):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = box
    px = im.crop((int(x0 * W), int(y0 * H), max(int(x0 * W) + 1, int(x1 * W)),
                  max(int(y0 * H) + 1, int(y1 * H))))
    data = list(px.getdata())
    r = median([q[0] for q in data]); g = median([q[1] for q in data])
    b = median([q[2] for q in data])
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return (r, g, b), (h * 360.0, s * 100.0, v * 100.0), len(data)


def run(rows):
    out = {}
    print("%-22s %-16s %-18s %s" % ("部位", "RGB中央", "H / S / V", "判定"))
    for (img, label, box) in rows:
        path = img if os.path.isabs(img) else os.path.join(SHOT, img)
        if not os.path.exists(path):
            print("%-22s 見つからない: %s" % (label, path)); continue
        rgb, hsv, n = sample(path, box)
        out[label] = hsv
        acc = ACCEPT.get(label)
        mark = ""
        if acc:
            bad = []
            if not (acc["h"][0] <= hsv[0] <= acc["h"][1]): bad.append("H")
            if not (acc["s"][0] <= hsv[1] <= acc["s"][1]): bad.append("S")
            if not (acc["v"][0] <= hsv[2] <= acc["v"][1]): bad.append("V")
            mark = "⭕ 受入値の中" if not bad else "⛔ 外れ: " + "/".join(bad)
        print("%-22s (%3.0f,%3.0f,%3.0f)  %5.1f° %5.1f%% %5.1f%%   %s"
              % (label, rgb[0], rgb[1], rgb[2], hsv[0], hsv[1], hsv[2], mark))
    have = [k for k in LADDER if k in out]
    vs = [out[k][2] for k in have]
    ok = all(vs[i] > vs[i + 1] for i in range(len(vs) - 1))
    print("\n⭐ 明度の階段 %s  %s"
          % ("⭕" if ok else "⛔ 順序が崩れている",
             " → ".join("%s %.1f%%" % (k, out[k][2]) for k in have)))
    return out


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--preset":
        run(PRESET[argv[1]]); return
    img = argv[0]
    rows = []
    for a in argv[1:]:
        name, rect = a.split("=")
        rows.append((img, name, tuple(float(x) for x in rect.split(","))))
    run(rows)


if __name__ == "__main__":
    main()
