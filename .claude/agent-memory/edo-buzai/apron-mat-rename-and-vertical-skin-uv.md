---
name: apron-mat-rename-and-vertical-skin-uv
description: 板の材の名を替えると "Soil" で板を探す C# が板を見失う・世界 XZ の材は立った面で縦の筋になる・0° の隅は --deg 0 だと M が付く(2026-10-12 岡部 第113巡)
metadata:
  type: project
---
- e399f0e6 で _Ago の板の材を Hifu_KitaTerrain_World へ替えたが、EdoBuild.MizoApronOf と岡部の吐き口の検めは材名 "Soil" で板を探していた ⇒ 板が無い扱いで板の下の地面が駒の最下点まで下がり、板の外の縁に 0.1〜0.3 の小口が立った。⭕ EdoBuild.ApronBody("Soil" と "_World")へ寄せた。
- Edo/TerrainSkinWorld は世界 XZ で引くので立った面は縦の筋 ⇒ SplatmapVert で層の模様の座標だけ水平の向きへ高さを展開(傾き 30° 以下は 0)。_Control は XZ のまま。
- build_kado の名は deg > 0 で素手 ⇒ 0° の隅(Kado(part,0f) = "00")は --deg 0.001 で焼く。zsh の for a in "…" で引数を渡すと割れず既定の 31.3 で Dobei_Kado_31 を上書きした(git checkout で戻した)── 1 本ずつ書く。
**How to apply:** FBX の材の名を替える前に、その名で部品を探す C# を grep する(BodyOfMat の第2引数)。関連 [[mizo-ago-terrain-sawtooth]] [[machiya-small-shops-hira-and-zsh-quoting]]
