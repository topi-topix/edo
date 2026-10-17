---
name: nozura-steep-grade-275-and-staged-meta
description: 野面の勾配の駒を ±0.275 まで剪断しても crest/holes は通る・継ぎ目は天端から測って ≤6mm・staging の meta は同類の G±120 から写せば externalObjects ごと remap 不要
metadata:
  type: project
---
2026-10-06 EDO-0502(岡部 外周の端の下げ打ち)で H0600〜H2400 × G±275 × a〜d の 56 駒と Mikiri_H2400 を staging に焼いた。
- 剪断 0.275 でも crest(背の下がり最大 +0.021)・holes(穴 0)は全駒 ⭕。継ぎ目は天端から測ると G0 と 54 点が一致、G− で最大 6mm ずれる(G+120 は 1mm)── 1mm で丸めた集合比較は偽の ⛔ を出すので最近点距離で読む。
- mikiri_h / grade の --render は OUT_WALL(= BUZAI_OUT)から G0 の駒を読む ⇒ staging では落ちる。G0 の駒を写した別の dir を BUZAI_OUT に指して撮る。grade の並べ焼きは --grade= を読むようにした。
**How to apply:** 勾配の駒を足すときは同じ見付の G±120(無ければ G0)の .meta を写し guid だけ替える。SannoNozura / SannoNozuraMikiriH は disk から最も近い物を引くので EdoAssets は注記だけ。[[nozura-grade-set-and-nearest]]
