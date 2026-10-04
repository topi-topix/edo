---
name: monomi-on-strip-and-saku-hikae
description: 隅長屋の物見は折る前の帯に出格子を付けると留めで L 字になる・build_nagaya_omote は import できるよう main を guard した・控柱つきの木柵は HoriSaku の部品を借りる(2026-10-04 松江松平 EDO-0554)
metadata:
  type: project
---
- `build_nagaya_kado.py --monomi`: 外隅(帯の原点)を中心に左右対称の出格子(`NO.add_degoshi`)を**折る前の帯**へ付けると、fold の二等分面で格子・膳板・小庇も留まり外隅を回る物見になる。札は front だけ出まで広げる(check.py 差 0.016)。
- `build_nagaya_omote.py` は末尾の `main()` を `if __name__ == "__main__"` で囲った(blender --python でも __name__ は "__main__")。他の生成器から add_degoshi / _boxer / win_extent を借りられる。
- 控柱は斜めの角材の端を面との交点で切る(頭 = 横板の内の面・足 = y −0.12)。水平断面の z の半幅は HB/2/|d.y|(HB/2 ではない)。札の foot・faceIn は控柱の足まで入る(faceIn ≈ −0.84)。
**Why:** 門口 h3.6・drop2.4 の門長屋は口の頭が土台の底 +1.2 で下段の窓(+1.07〜)に 0.13 掛かる ── 指図の値のまま焼いて申し送った。
**How to apply:** 隅の駒に付け物をするなら帯の段で対称に付けてから折る。[[nagaya-kado90-fold-and-spec-band]] [[nagaya-mon-short-pier-window-sliver]] [[tategoshi-saku-module-and-hori-saku-axis]]
