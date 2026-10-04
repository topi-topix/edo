---
name: foot-bottom-batter-and-stair-front
description: 皮の塞ぎ・床が隅の駒の法の途中を底と読み +0.17〜0.28 の三角の歯(WallBottom(0.2) も目地の段 16.85 を返す)。石段が面の外に立つと設計の地盤の勾配が段の前に土の斜面を被せる。外周の石垣を部材に渡さないと皮が見え面に土の三角を描く
metadata:
  type: project
---

2026-10-04 EDO-0502 第10巡(岡部 Stage3b・門の内の隅 TW_Kado_Shumen_kado2_3_0 / 石段 K_Dan1 / 基壇 IG_S_Hei_21)。

1. 歯: 塞ぎ(sealFace)の nb = 近く ±0.25 の min(Bottom, WallBottom(0.2)) の最大。殻の隅の駒は Bottom = 法の面(16.71〜17.36)、
   WallBottom(0.2) も小さな石の面の下の縁(16.85〜16.93)を返す ⇒ 面 16.50 + 許容 0.28 の内で皮を盛った。
   直し: `TopIndex.FootBottom` ── 最も低い面が下を向いた面(本当の底)でなければ見え面の足の線(WallBottom 0.2 と 0.6 の低い方)。塞ぎ・床で Bottom の代わりに使う。
2. 石段の前の土: 門の内の面の多角形は石段の 1m 手前で切れ、間は設計の地盤(上の面へ上る勾配)。石段は帯で篩わないので 3b も効かない。
   直し: 帯で篩わない・下向きの底を持つ駒の外形の中は面か底へ下げ、外 NEAR 内は底から 1:batterFill の高さで頭打ち。
3. 基壇の土の三角: 皮は渡された駒しか知らない。段の土留めの穴の升が外周の石垣の見え面に掛かると、設計の地盤を見え面の上に描く。Stage3b で段の駒に接する Ishigaki を部材+帯へ。

**How to apply:** 皮の「歯」「被り」を指摘されたら、まず TopIndex を reflection で起こして問題の点の Bottom/WallBottom/FootBottom を刷る(1 回で原因の規則が分かる)。
関連 [[batter-toe-read-as-bottom]] [[skin-edge-across-nozura-face]] [[wall-seat-on-skin-ground-not-grid]]
