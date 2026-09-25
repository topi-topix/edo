---
name: nori-cut-step-and-sode
description: 鉛直な段石・袖を野面の法 1:0.25 に突き付けるには駒の端を法の面で切る。跨ぐ端は凸な部品に分けて切る・bisect の交点は検算の丸めの升目を外す・EdoAssets.cs は他セッションの claim を先に見る
metadata:
  type: project
---

2026-09-26 EDO-0442(`build_sanno_buzai.py -- sode_nori / dan_kiri_list / kiri_shots`・`Own.IshidanSodeNori` / `Own.SannoDanKiri`)。

- 凸でない切り(隅の塊を抜く・膝で法を止める)は、複製して**凸な部品ごとに半空間で bisect → 切り口を holes_fill → join**。内側に重なる蓋は見えない。外の面の UV は bisect の補間で連続。
- ⛔ 検算の罠: `check_mirror_x`(1e-4 の升目の集合比較)は bisect の交点で偽の不一致 ⇒ KD 木の最近傍で比べる。面の上の頂点を `< 0` で側へ振ると偽の食い込み 0.28 ⇒ 帯 1e-4 を袖の側に数える。
- 端の値(d・za)は据えた後の従属値 ⇒ 一覧 `sanno_sando_kiri_set.txt` で焼く。棟梁の記録から逆算した段 2 の d 0.156 が棟梁の実測の最大と一致 ── 法の式の向きの検算になる。
- ⚠ python の heredoc で EdoAssets.cs を書くと門番(edo_guard)をすり抜ける。他セッションが claim 中でも書けてしまった ⇒ 書く前に `edo_session.py` の claim を見る。

**Why:** 中ほどで突き付けても上下に 0.25×丈/2 の口とめり込みが残り、許容0を破る。
**How to apply:** 鉛直な駒が法の面に当たると言われたら、据えではなく駒の端を法の面で切る。関連 [[ishidan-sode-sheared-module]] [[sode-depth-variant-for-groundhi]]
