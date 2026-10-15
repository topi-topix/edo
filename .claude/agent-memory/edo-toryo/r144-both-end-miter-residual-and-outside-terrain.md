---
name: r144-both-end-miter-residual-and-outside-terrain
description: 岡部 第144巡 ── 両端を留める長屋の札の余りの行き先(入隅一つならそこ・他は半分ずつ・硬い ±0.002)・区画の外の地形の動きは S1 の戻し+道の帯と S3d の駒の下・S_Hei_08_0_1 の浮きは N12_0 が建たない端
metadata:
  type: project
---
2026-10-16 EDO-0502 第144巡。

1. **両端を留める棟の余り**: ReplaceWithMiterCut が lo の Q へ合わせ切ると余り(札 − 要る長さ)が全部 hi の越えになる。
   直し(EdoBuildTsugime.cs): 長い分は入隅の端が一つだけならそこへ全部(相手の躯体の中・埋めて隠す)、他は半分ずつ。
   PickMiterCutOrWait(bothEnds, endTol, oneConcave) が半分ずつの版を |余り| ≤ 2×tol でなければ採らない(硬い)。
   ⚠ 硬くした途端に N13_0(両端とも出隅・札 15.090 / 要る 15.081)が待ちへ ⇒ 部材方へ「要る長さ −0.0002」で焼き直し。N12_0 は相手が直角の妻のままで頂点13 で落ちる(N13_0 待ちの連れ)。
2. **区画の外の地形の動き(622 節点・0.333)** は全部 線の外 2m の内: S1 の RestorePerimeterSpill_(両向き 0.02・base_dem へ)と道の帯(michiNarashi)が上げ下げし、
   S3d が駒の外形の下(基壇の見え面は区画の外)を下げ、最後の戻し(r137b T3)が駒の下を skip する。S1→S2→S2b→S3 の間は区画の外 0。
   分けるのは scratchpad の bin 6 枚(pre/S1/S2/S2b/S3/S3d)を python で差し、駒の下/指図の道の面/隣の区画/説明の無いの 4 つに分ける(NearHulls)。
3. **S_Hei_08_0_1 の足の浮き 0.795** は石(隅の石垣 IG_S_Hei_08_0_0_x_0_kado)の法の面の上を測った物。(推定・未確認)端は頂点12 で N12_0 に受けられる筈が、N12_0 が建たず塀の端が石の天端の外へ出た ── N12_0 が建った巡で測り直す。
4. NearHulls(全駒) を execute_code で呼ぶ計測は 30 秒を超え 6 回走る(12 分ふさいだ)── 流しの中の印つきの一手に入れる。
5. スワップは S2 の間に 9.4→10.6GB。流しの前に測り、10GB 超なら止める指示がある巡は S2 の後で止めて残りの手(chainB)を scratchpad に残す。

**How to apply:** 両端の留めの版は待ちの「要る長さ」を ±0.002 で焼かせる。区画の外の動きの申告が来たら bin の段ごとの差で書き手を割る。関連 [[r143-miter-default-plane-and-parallel-buzai]] [[michi-narashi-outside-parcel]]
