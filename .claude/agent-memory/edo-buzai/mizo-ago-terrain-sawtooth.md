---
name: mizo-ago-terrain-sawtooth
description: 地際の板の材は地形の塗りを世界XZで引く Hifu_KitaTerrain_World。天端=地表で据えた細い溝(全幅0.54)は 0.25m 格子の地形が縁石の外に鋸の歯を立てる ⇒ 地際の土の板 _Ago(出0.40・厚0.36)で覆う(2026-10-11 岡部 EDO-0502 第111巡)
metadata:
  type: project
---
- 溝の中の地形の節点を下げると、外の帯の節点との三角形が縁石の外面の前で谷になり外面が歯形に覗く。出は格子の対角 0.354 を覆う 0.40、厚さは吐き口の底 −0.30 より深く 0.36。
- 検めは傾けた 0.25m 格子の模型地形(_mock_terrain・溝の中の節点を下げる)に据えて before/after を並べる。平らな地面の検めでは歯が出ない。
- 板の材は ⛔ FJG Soil でなく `Hifu_KitaTerrain_World`(第113巡: Soil の板は据えると落葉混じりの橙の帯)。シェーダ Edo/TerrainSkinWorld が世界 XZ を地形の正規化座標へ写し、地形のスプラットと層をそのまま引く(層 0〜3 を正規化した一枚・FBX の uv は無視)。_Control は Unity でしか結わえられない ⇒ EdoBuild.SkinWorldMaterial(t) を建てる度に呼ぶ(結わえないと既定の赤 = 層 0 の土一色)。
- 板は内側(石垣の側)にも張り左右対称に保つ(片側だと向きに意味が出る)。曲がりの外側は板どうしが開く(未対処)。
**How to apply:** 地表と面一に据える細い部材全般(溝・縁石・敷石)。関連 [[haisui-modules-holes-and-soil-scale]] [[flush-masu-skirt-and-scaled-kado-h]]
