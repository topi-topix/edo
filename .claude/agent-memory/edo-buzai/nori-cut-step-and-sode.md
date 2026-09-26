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

2026-09-26 追記(EDO-0430): 端を平面で斜めに切る型 `dan_kiri` の `d±A±[N±]`(`Own.DanKiriEnd(d, deg, nori)`)。
- d は踏面の中心 Z=0・蹴上の中ほどで測る。角が大きいと坂下の端が小口の外へ出る ⇒ 伸ばしてから切る(`_stretch_end`)。
- 法 0 は綴りに N を出さない(C# と揃える)。値が無い段は `dan_kiri_try` で型だけ刷り、焼かない。

2026-09-26 追記(EDO-0437 第3巡・`build_sanno_nozura.py -- nnori / sode_nori`・`Own.SannoNozuraNoriEnd` / `Own.IshidanSodeNozuraNori`):
- ⚠ 野面の法は **1:0.3**(焼いた駒の前の包絡を段ごとに測っても 0.3 で平行・+0.065〜0.08 の出)。棟梁の「1:0.25 相当」・切石の袖の NORI 0.25 を流用しない。
- ⛔ 法で切った端の駒は scale.x で法が変わる ⇒ 伸縮させず長さの刻み(0.05)で焼く。窓の継ぐ側を 1間の継ぎ目に置けば直線の駒と頂点まで一致する。
- 袖の背を法で切ると膝(−0.60)の下が痩せる: 法 0.3・踏面 0.542 では e −0.30 で駒が消える ⇒ e は −0.25 まで。

2026-09-27 追記(EDO-0459・`-- sode_flat_nori`・`Own.IshidanSodeFlatNori(depth)`): 水平の袖の坂上の小口(局所 −Z)を `_clip` 1 面で切るだけで済んだ(石は箱なので凸)。
- 面は天端の稜 (Y=HT, Z=−L/2) を通す ⇒ 天端長は不変・丈 3.20 だと底が Z +0.175 まで痩せる(1.25 で足りる)。
- ⚠ 据え手の Z 伸縮で法も同じ比で変わる(1.009 倍で 1:0.252)── 大きく伸ばす所では `--len=` で実長を焼く。
