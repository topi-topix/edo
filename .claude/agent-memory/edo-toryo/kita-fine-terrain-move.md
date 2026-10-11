---
name: kita-fine-terrain-move
description: 2026-10-11 皮をやめ北の3邸を 0.25m の細かい地形 KitaTerrain へ移した ── T() は名指し(TerrainFocus)・座標は TerrainAt・3b は溝も据えていた・計測は focus の中で
metadata:
  type: project
---

2026-10-11 EDO-0502 第110巡(施主裁定: 皮 EdgeSkin/SkinHeightSolve をやめ 512m・0.25m の地形一枚へ)。

1. 地形が二枚になった: ModernTerrain(2m・北の範囲 256² 升を穴抜き)+ KitaTerrain(原点 −817.88/858.07・2049²)。
   `EdoBuild.T()` は**名指しが無ければ一番大きい地形** = ModernTerrain(穴の中)を返す。岡部の Stage は `OnKita()`(TerrainFocus)で囲ってある。
   **execute_code で測るときも `using (EdoBuild.TerrainFocus(区画の芯))` で囲む** ── 囲まないと Drawn()/DrawnGround は穴の大地形を引く。
   `Ground(x,z)`・`Probe()` は座標で細かい方を引くので囲まなくてよい。
2. 旧 Stage3b_Hifu は**皮の前に溝 6 種(PlaceOmoteGesui〜PlaceSeRojiAnkyo)を据え、皮の後に練塀・垣・縁・門を床へ据え直していた**。
   3b を外すだけだと溝が建たない ── Stage3d_Mizo に移した(+ SinkGroundUnderMizo)。
3. 土井・松江松平は大地形の高さと穴(皮の升 1542)を写しただけ。彼らのビルダーが T() で書くと穴の大地形へ書いて見えない
   ── 移すときは Stage を TerrainFocus で囲む一行が要る。
4. 地形の新設は 2.0 秒(SampleHeight 420 万回)・資産 24.2MB。大地形の木 999 本を移して外した(穴の升の木は描かれない)。

**How to apply:** 北の3邸で測る・建てる・地形を書く C# は必ず focus の中で。大地形へ戻す時は scratchpad r110 の ModernTerrain_r110_pre.asset。
関連: [[contact-must-use-drawn-surface]] [[skin-solve-lo-hi-first-runs]]
