---
name: water-defaults-are-for-deep-ponds
description: 水が乳白色・汀に白い縁が回るのはシェーダの既定値(深さ4m前提)のせい。Depth/Opaque でも地形の分解能でもない
metadata:
  type: project
---

**症状**(2026-09-21 松江松平の御泉水・施主指摘): 水深も水面の高さも実測で正しいのに、絵では
**面の中ほどまで乳白色に濁り**、**汀の全周に幅 2m の白い縁**が回って水に見えない。

**原因**: `WaterBaker.NewBody` が起こすマテリアルの既定が **深さ 3〜4m の溜池・堀向け** —
`_DepthFade` **4.0m**(この距離で初めて `_DeepColor` に届く)/ `_ShoreWidth` **1.5m** +
`_FoamAmount` 0.4(岸なじみの帯)。深さ **0.90m** の庭の池に当てると、池のどこも深い色に届かず
**全面が `_ShallowColor`(明るい 0.28/0.50/0.55)**になり、1.5m の帯が**白い縁**として全周に出る。
⛔ URP の Depth/Opaque は **ON**(`Assets/Settings/PC_RPAsset.asset` で確認済み)。
⛔ 地形の分解能(2.0 m/px)でもない — `_FoamAmount` を 0 にしただけで白い縁は消えた(実験レンダ)。

**見分け方**: マテリアルは**水域ごとに1枚**(`Assets/Edo/Water/Water_<時刻>.mat`)。
`_Alpha 0.8 / _DepthFade 4 / _NormalStrength 1 / _WaveStrength 0.06` なら**既定のまま**、
`_Alpha 0.95 / _DepthFade 3.5 / _NormalStrength 0.35 / _WaveStrength 0.03` なら**手で寄せてある**。
2026-09-21 時点で赤坂の 6 水面のうち 2 枚(溜池・堀)が寄せてあり、**4 枚が既定のまま**。

**対処**: `WaterBaker.NewBody`(`Assets/Edo/Editor/WaterBaker.cs`)で **深さから起こす** —
`_DepthFade = max(0.8, depth)` / `_ShoreWidth = clamp(depth*0.35, 0.25, 1.5)` /
`_FoamAmount = depth>=2 ? 0.4 : 0.1`。既存の水域はマテリアルが別々なので**自動では直らない**
(直すなら1枚ずつ。他邸に当たるので勝手に流さない)。庭の池の見本は `P_DoiOkuniwa.mat`(土井)。

⚠ **真上から見ると水はほとんど見えない**(Fresnel でほぼ透過)。池底が陸の地表(土・草)のまま塗られて
いると**濡れた原っぱ**に見える ⇒ 底の塗りは別口の宿題。

関連: [[pond-carved-but-water-lost]]
