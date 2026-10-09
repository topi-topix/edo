---
name: skin-over-battered-face-vertical-strips
description: 野面の隅・継ぎ目の「縦の土の帯」は皮の三角形 ── 外形の中の節点が天端の下(cap)に留まり、下ほど前へ出る法の見え面の上へ 0.3〜0.9 出る。画素から光線で名指してから直す
metadata:
  type: project
---

2026-10-09 EDO-0502 第65巡(岡部 K_Dan1 の脇の返し・隅 kado11・Side0_0_006f・Side1_0_014f)。写真 r64 の隅の駒の縦の茶色の帯。

**名指し方**: 検証レンダと同じカメラ(r6x_kdan1_shots の式)を作り、`cam.ScreenPointToRay(画素)` を一時の MeshCollider へ打つ。
先着は EdgeSkin(材 Hifu_ModernTerrain_0・法線 y 0.1〜0.3 = ほぼ鉛直)、石の見え面の手前 0.03〜0.1。三角形の頂点を真上から駒へ下ろすと、
一つの頂点が真下の見え面より 0.86 上(20.45 / 面 19.59)── 3b「見え面の前へ皮を出さない」は外形の中の点しか下げず、石段など前の部材に
光線が当たると「石の後ろ」と読んで残す。

**直し**: NozuraCrestCover.Ceiling(言い直し 2026-10-09b の天井と同じ所): 見え面の前の縁より前で外形の中の節点は、真下の石の面 − capDrop へ。
周りの最も低い節点から 0.3 より上に立つ節点だけ(根入れの上の足元の土は掘らない)。

**How to apply:** 色の帯・染みは材を疑う前に画素から光線で先着の物と材(triangleIndex → submesh)を取る。⚠ 8GB 機で Stage3b は 60 分(第64巡)。
関連: [[skin-edge-across-nozura-face]] [[named-face-not-normal-to-line-sawtooth]]
