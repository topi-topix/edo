---
name: castlewall-face-is-local-minus-x
description: Castle Wall の見え面(法の面)は局所 −X。山王 Stage3 は +X を外へ据えるので土留め 233 駒中 162 が法の面を高い側へ向け、低い側に鉛直な背を見せている
metadata:
  type: project
---

2026-09-25 EDO-0430 で測った。`JC.CastleWall` は x∈[−2.4,0](下)/[−1.4,0](上)── 法の付いた面は局所 −X、x=0 は鉛直な背
(両方に石の材が貼ってあるので絵では裏返りに気付きにくい)。Stage3 の注記「見え面 = +X」は誤りで、`outw` を +X に当てる
ため郭・腰石垣・前庭の土留めは法の面が土の中、回廊の基壇だけ(票の読みが逆に出て)正しい向き。
`EdoBuild.FaceSide`(下の帯が前へ出る側)と `WallFaceRise`(見え面の前 − 背の後ろの地表)で測れる。HifuMeasure が刷る。

**Why:** 翻すと駒の体が線の反対へ 1.4〜2.4m 出る(線 = 背の線のまま回すと面が広がる)── 線が背か天端の前の縁かは指図の話。
**How to apply:** 向きを直す前に「run の線 = 背 / 天端の前の縁」を普請奉行に確かめる。TuckUnderCrest に渡す faces も +X なので同時に直す。
隅の駒の据え(`PlaceRunKado`)は向きを実メッシュで測るのでこの誤りに引きずられない。[[crest-burial-count-picks-batter-face]]
