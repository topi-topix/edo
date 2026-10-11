---
name: kadoarms-pivot-is-line-intersection
description: KadoArms の据え点は両辺の外面の線の交点 ── 辺ごとに控えが違う隅で「深い方一つ × tan(δ/2)」にすると据え点が控えの差だけずれる(岡部 P3 で 0.31 の口)・隅でない端の止めは freeEnd で渡す・型H の段落ちは壁の丈 0.49 で型A と継ぎ目に段が残る・KitaTerrain に旧い皮の穴が 3343 升残っていた
metadata:
  type: project
---

2026-10-12 EDO-0502 第116巡(岡部 角 P0 の南)。

1. **症状**: 辺3 に 0.31 の口(P3 の出の腕の先 s2.22 / P4 の入りの腕の先 s2.53)が、頂点ごとの控えに直しても消えなかった。
   **原因**: FitKado の KadoFace は**辺ごと**の控え(辺2 = c0.41 + 犬走り 0 / 辺3 = c0.42 + 0.30)で両腕を寄せる ⇒ 据え点は両辺の内寄せ線の交点。
   KadoArms は深い方 0.72 一つで `d·tan(δ/2)` を取っていたので、90° の P3 では据え点の s が 0.72 − 0.41 = 0.31 食い違った。
   **対処**: `EdoBuild.KadoArms(..., Func<int,int,float> faceInAt(辺, 頂点), wallT, ..., freeEnd, ...)` ── 交点の距離 (d_相手 − d_自分·cosδ)/sinδ(|sinδ|<0.05 は平均 × tan)。旧い定数の版は同じ値(松江松平は不変)。
2. **症状**: P2 の入りの腕 4.11 が辺1(3.31)を越え N41_5 の妻と留め柱を貫いた。**対処**: 留め柱を隅より先に据え(`PrePlaceTomeForKado`)、腕の先 t ∈ [柱の近い面, 遠い面 − 重ね] を `freeEnd` で渡す ⇒ P2 = `Dobei_Kado_00_A180x50`(部材方へ)。
3. 型H(Doi_DanOchi)は側の壁の丈 = 底 + 0.49 ── 型A(深さ 0.10〜0.30)と継ぐと継ぎ目で天端が 0.2〜0.4 違う。地表なりに埋める `LayDanOchiOnGround` と両脇の帯 `FlushGroundToStepTop`、型H の後の型A は `headTop = 上流の底 + 最も深い版` で沈めて続ける。浅い壁の版は部材の話。
4. KitaTerrain の穴 98,767 升のうち、皮(EdgeSkin)の頂点が 1m 内に無い升 3,343 は旧い岡部の皮の穴(z≈950 の旧い南の線・西の端)。井戸の穴(三べ坂西の渡辺・鳥居 各 128)は残す。
   測り方: プレハブ資産の EdgeSkin の頂点を吐いて穴の升と突き合わせる(⚠ 全プレハブを舐めると 30 秒を超えて再送される ── 印を付けて書き出すだけにする)。

**How to apply:** 隅の駒の腕を選ぶ・測るときは、辺ごとの控えを FitKado と同じ関数で渡す。皮を退けた邸は、その邸の旧い区画の線に沿って穴が残っていないか数える。
関連: [[kadoarms-per-vertex-facein-and-free-end]] [[mizo-flush-top-rigid-pieces]] [[kita-fine-terrain-move]]
