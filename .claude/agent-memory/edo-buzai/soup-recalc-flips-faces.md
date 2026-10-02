---
name: soup-recalc-flips-faces
description: VM.Mesh は頂点を溶接しない面のスープ — bmesh の recalc_face_normals は面1枚ずつの島で向きをでたらめに決め、表店の妻が背景へ抜けた(2026-10-02 EDO-0503)
metadata:
  type: project
---
- 表店 Typ_Omotedana*/Hira の妻(漆喰の断面・下見板・水切り)が裏返り、Unity で背景が抜けた(施主指摘)。原因は `_recalc` = recalc_face_normals を溶接しないスープに掛けたこと。⭕ `VM.orient_outward(obj, m.gid)`(box/section ごとに重心から外へ)に替えた。
- 既存の検証②(内から撃って当たるか)は裏返った面にも当たるので ⭕ のまま見逃した。⭕ 外から撃ち**裏向きの面は素通り**させて最初の表の面を見る(`tsuma_audit`)。旧 23,298 抜け → 0。
- マゼンタは world の色にすると光まで染まる ⇒ film_transparent で刷って PIL で合成する。⚠ 同じ recalc を VM のスープに掛けている生成器が他にも在りうる(kuri / sanno_* ほか)。
関連 [[magenta-background-finds-holes]] [[recalc-normals-inverts-folded-stone]] [[mesh-box-inward-normals-and-ray-checks]]
