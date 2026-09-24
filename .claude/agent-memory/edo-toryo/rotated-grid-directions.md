---
name: rotated-grid-directions
description: 境内の軸を回した邸(山王 5.5°)では、方位の語(front=東…)も uv→世界も枠の回りを足さないと門が建たず社殿が元の軸に残る
metadata:
  type: project
---

症状(2026-09-24 EDO-0430): 山王の grid.keidai を 5.5° 回した後の建て直しで、Stage5 が門4基を「焼いた yaw 5.5 と部材の軸から出る 0.0 が食い違う」で建てず、
Stage6 の社殿は z=847.00 ちょうど(回っていない uv→世界)・yaw 0 で据わった。石段・土留め・囲いは算出物の world 座標なので正しく回っていた。
原因: `EdoSannoShaRebuild.W()` が `x0 + u×ken` で基底 ux/uz/vx/vz を掛けていなかった。`EdoBuild.FaceYaw`/`DirVec` は世界の方位しか知らなかった。
対処: `EdoBuild.FaceYaw(front, axis, frameDeg, out)` / `DirVec(compass, frameDeg, out)` を足し、山王は `EdoSannoShaRebuild.GridDeg`(grid.keidai の u 軸から)を渡す。
向きが未宣言の棟の既定の姿も「枠に沿う(yaw = GridDeg)」にした。⚠ 回した枠を持つ邸を他に起こしたら同じ所を見る。

別件の小さな罠: 呼び出し元が検分の記録(reviews)を指図へ書くと指紋が変わり、全 Stage が「算出物が焼かれていない」で止まる。
`bake_impl.py sanno` で食い違い 0 を確かめてから `--write`(指紋だけ刷り直る)。

関連: [[front-axis-differs-per-part]] [[sanno-stage6-clears-before-fingerprint]]
