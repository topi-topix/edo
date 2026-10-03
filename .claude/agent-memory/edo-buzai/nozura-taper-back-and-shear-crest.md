---
name: nozura-taper-back-and-shear-crest
description: 野面の表の石を尻すぼみにすると、勾配の駒でだけ crest が落ちる — 剪断が背の丸みの面を寝かせ nz>0.7 の篩に掛かる。芯を天端の帯へ上げる
metadata:
  type: project
---

2026-09-26 EDO-0437 施主指摘「真上から表の石が長方形に切り取られている」で `build_sanno_nozura.py` の `_taper_back` を入れ 158 駒を焼き直した。

- ⚠ G0 と G+ は crest ⭕ なのに **G− の 40 駒だけ背の下がり 0.056 ⛔**(全駒で同じ端の石・同じ点)。原因は天端の列の石の背の丸みの芯 Cb を石の半ばの高さに置いたこと: 上の縁から芯へ緩く下る三角が、剪断で法線が傾き nz 0.68→0.74 と篩(0.7)を越えた。⭕ 天端の列は芯を天端の線の 0.025 下へ(TAPER_CAP_TOP)。
- ⛔ 端の石の縮みを浅くする手(kb ≥ 0.8)は逆に G0 まで落とした。形を変える前に、落ちた格子で「どの塊のどの三角か(nz と高さ)」を割り出すこと(scratchpad の who2.py の型: 分離した塊ごとに crest の up_grid を再現)。
- ⚠ Blender の既定の Cube: probe で read_factory_settings(use_empty=True) を忘れると光線が z=1 の平面に当たり嘘の表が出る。

**Why:** 勾配の駒は剪断なので、同じ石でも面の向きが駒ごとに違う。G0 だけ見て通すと負の勾配で落ちる。
**How to apply:** 野面の石の形を変えたら crest を G− / G0 / G+ の三つで回してから全駒へ。関連 [[nozura-back-crest-flush]] [[nozura-crest-omote-ura-two-rows]]
