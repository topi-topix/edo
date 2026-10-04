---
name: nozura-kado-oblique-fold
description: 野面の出隅を 90° 以外の折れで焼く(kado_deg)── σ の割りは t=tan(折れ/2) で一般化・裏石は腕ごとの直線の駒を留めの線で選ぶ・make_wall は V.reset する(2026-10-05 EDO-0502)
metadata:
  type: project
---

`build_sanno_nozura.py -- kado_deg --deg=49.4,51.8 --h=4.8`(名の角は丸め `Sanno_Nozura_Kado49/52_H4800_<a|b>`)。
- 法の出 c の面どうしの稜線は c·(t,1)・t=tan(φ/2) ⇒ `kado_layout(t=)` の W = 0.909 + c·t・lift_ds も BATTER·t。腕2 は直線の駒を yaw φ で回した (x,z)→x·d2+z·n2(d2=(cosφ,−sinφ)・n2=(sinφ,cosφ))。90° は厳密値で旧版と同じ式。
- 裏石の正方形の割り(kado_ura)は 90° 専用 ⇒ 腕ごとに `wall_ura` を起こし、重心が留めの線から 0.06 以内の石だけ採る(切ると上から留めの直線が見える)。目地の底の板だけ留めの線で切る(塞がない)。腕2 の先は `bm_cut_keep(chip=0)`(斜め面)。
- ⚠ `make_wall` は `V.reset()` する ⇒ 継ぎ目の基準の点は隅の駒を起こす**前に**採る(後だと StructRNA removed)。焼く前の表からの光線の裏当たり 4 本は FBX に読み戻すと 0。

**Why:** 岡部の東の土留めの折れ 49.4°/51.8° に隅の駒が無く、外の角に足元 0.79m の楔が開いた。
**How to apply:** 他の角度も同じコマンドで焼ける。据える側(EdoBuildNozura の turn<60 の分岐)は腕2 が 90° でない前提に直す要あり。関連 [[okabe-dan-kado-angles-and-deep-nozura-kado]] [[nozura-kado-sigma-fold]]
