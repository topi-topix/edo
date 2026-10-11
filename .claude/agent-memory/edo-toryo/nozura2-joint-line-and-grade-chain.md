---
name: nozura2-joint-line-and-grade-chain
description: 重ねの端の野面 Nozura2 は射影の端で連ねると重ねの分だけ離れる・坂の天端は勾配の連鎖で継ぐ・crestOf は傾いた天端で高い側に偏る(2026-10-11 EDO-0502 第104巡)
metadata:
  type: project
---
岡部の継ぎ目の隙と段差(施主の写真2枚)を部材 Nozura2(両端を 0.02+0.026·深さ 延ばした版)で直した巡。

- 症状: Nozura2 を旧の連ね方(実メッシュの走りの射影 span の端どうし)で並べると、重ねの分(H4.8 で片側 0.15)だけ駒が離れる。
  原因: 射影の端は根入れの底の重ねの先。対処: `PlaceNozuraRun` の `jspan` = span − |lossyScale.x|·`Nozura2OverlapMax(焼いた H)`
  (Unity で測って 0.909+ov と 1mm で一致: H0.6 0.950 / H2.4 0.997 / H4.8 1.060)。
- 症状: 坂の線(勾配 0.69)で駒ごとに天端が段。原因: 中ほどを線へ据え・勾配は線に最も近い物 ⇒ 焼いた勾配の外れが継ぎ目ごとに段。
  対処: 前の駒の終わりの天端から連鎖(勾配 = (次の継ぎ目の線の高さ − 今の天端)/走り)。
- 罠: `crestOf`(天端の帯の上位 40% の中央値)は傾いた天端で高い側の筋に偏る(0.69 で +0.1 前後)⇒ 勾配を差し引いて測る `crestOfG`。
- 岡部だけに効かせる手立て = 邸ビルダーの straight を `EdoAssets.Own.Nozura2` に渡すだけ(EdoBuild 側は `IsNozura2` で分岐 ⇒ 山王・土井は旧のまま)。
- 岡部の RunAll は約 1 時間(印のファイル r104_all.mark で再送を止め、read_console のタイムアウトで待つ)。

**How to apply:** 野面の駒の版を替えるときは、まず焼いた札(重ね・勾配の段)を Unity で 1 駒測ってから連ね方を変える。[[nozura-wall-traps]] [[measure-dont-nudge]]
