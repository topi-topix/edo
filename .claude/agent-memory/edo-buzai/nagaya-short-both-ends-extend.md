---
name: nagaya-short-both-ends-extend
description: 両端を留める短い表長屋(3.75)は据え置きの割付が組めず --extend で焼く・--cut-kera に tani は書けない・門長屋は s0 側の版も要る(2026-10-17)
metadata:
  type: project
---
- 両端 θ≠0(段の低い端 0.01 + 入隅)の駒は cut_miter_anchor が駒の長さで割付を解くので 3.75 は「全幅 4.394 は作れない」で止まる ⇒ `--extend`(第155巡で足した)で延ばして組んで切る。両端の探索幅を 0.6 で打ち切ると窓が Q に乗る(離れ 0.006)── --extend は全幅で探し 0.79。
- `--cut-kera` の引数に `tani` は通らない(hi|lo|sumi|0)。入隅の端は "0" と書けば既定で谷になる。札の source には tani と出るので写すと止まる。
- 門長屋の版は C# が先に s0 側から測った gc の版(mon3.27)で据え、向きを見て引き直す(mon4.07)⇒ 両方焼く。辺18 は局所 +X = s の増える向き(14.62_mon4.07 と同じ)なので本命は mon4.07、mon3.27 は lo を +X 側に置いた鏡の版。

**Why:** N17_k・N18_0 を焼く巡で三つとも踏んだ。**How to apply:** 短い両端留め・門長屋の版を焼くとき。関連 [[dan-seam-low-end-flat-cut]] [[iri-sumi-tani-valley]] [[nagaya-miter-cut-signed-anchor-seal]]
