---
name: hatake-une-paving-dirt-and-seam
description: 畝など土の盛りは FJG の M_FJG_Terrain_Ground_Soil_01 を 8m 周期・茶の矩形で。Paving と Meadow の土は灰色の丸太に見える。継ぐ駒の端の高さ落としは 6% まで(2026-10-03)
metadata:
  type: project
---
土の盛りの材は **`M_FJG_Terrain_Ground_Soil_01`**(地形のスプラット L_dirt と同じテクスチャ・タイル 8m)。UV 1.0 = 8m で地形と粒が揃う。1間の駒が使う u0.114×v0.095 を**苔の無い茶の矩形**(左下 u0.008/v0.900)に取り、u を芯で折り返すと継ぎ目で柄が切れない。小口(n角形)は折り返すと扇で u が化ける → 線形のまま。
⛔ Village Kit `Paving` の土の象限と Meadow の `*_Soil_01` / `*_Wet_Soil_01` は平均色の R−B が 11〜27 で、85 駒並べると**灰色のコンクリートの丸太**に見えた(FJG は 68)。候補は平均色の R−B で先に篩う。
継いで並べる駒の端の高さを 15% 落とすと 1間ごとに節に見えた → 6%。
**Why:** 畝(Own.HatakeUne・EDO-0532)で 2 度踏んだ。**How to apply:** 土・地面の新造は FJG Soil を借り、remap は岡部の新造メニュー(FJG/Materials を見る)で足りる。FBX の .meta の externalObjects を書き換えれば remap も要らない。
