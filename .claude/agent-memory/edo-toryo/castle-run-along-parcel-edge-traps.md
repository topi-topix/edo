---
name: castle-run-along-parcel-edge-traps
description: 区画の辺に沿う城の石垣・長屋・練塀の4つの罠 ── 指図の s の丸め・90°超の出隅・駒の実長・疎な駒の Contact(土井 S2 2026-10-04)
metadata:
  type: project
---
土井 S2(EDO-0533)で `EdoBuild.PlaceCastleRun`(EdoBuildShiroIshigaki.cs)を書いたときに踏んだもの。

1. **指図の s は 0.01 で丸めてある** ── 辺13 の s1=77.26 と実の辺の長さ 77.264。「端が頂点か」を `Len − 1e-3` で見ると外れ、相手の無い出隅の詰めが黙って効かなかった(0.252m 区画の外)。`EdoBuild.VTX_TOL`(0.02)で見る。
2. **出隅の折れが 90° を超えると、線から内へ控えた駒ほど隣の辺の外へ出る**(内の距離 = t·cos φ)。長屋の妻の腰が 0.35m 出た。⇒ 走りに沿って引く `EdoBuild.PullAlongInside`(腰 1.2m で測る・軒は越えてよい)。
3. **Castle Wall の実長は送り 2.00 より長い** ── 区間の端の駒が端から出る。相手の無い端は端の駒を引く。口の脇の 2m 未満の切れ端は PlaceCrestWall が「両側へはみ出す」ので口の中へ 0.56m 出た ⇒ 口の縁から一枚据え、反対の端を高い隣の区間の裏へ延ばす。
4. **Castle Wall は頂点 76 個** ── `Contact` の筋 0.25/0.5m では共通の筋が無く NaN。筋 1.0m で測る(投影の端どうしでも検めた)。

**How to apply:** 区画の辺に沿う run を据えるときは PlaceCastleRun / PullAlongInside を使い、頂点の判定は VTX_TOL で。関連 [[contact-cell-too-fine-on-sparse-meshes]] [[kado-arm-overruns-short-edge]]
