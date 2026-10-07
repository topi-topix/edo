---
name: sode-uchikomi-texture-lattice-cycle
description: 段ごとの駒に城の石垣の連続した肌を貼るときは駒の周期を a/b でなく N にする — N 駒のずれをテクスチャの 2.0m 格子へ載せる
metadata:
  type: project
---

2026-10-07 EDO-0502(岡部 K_Kuruwa・`build_sanno_buzai.py -- sode_uchikomi`・`IshidanSodeUchikomi_*_{a..i}`)。

- Castle Wall の `stone wall` は 1m = UV 0.25。石積みの帯は u 0.25〜0.75・v 0〜0.5 がどちらも周期 0.5(= 2.0m 角)で継ぎ目なし。v 0.5〜0.75 は天端の一段だけ・0.758 から上は砂。
- 駒は (踏面, 蹴上) ずつずれるので、a/b(0.90, 0.566)では柄が駒の境で切れる。N 駒のずれを格子に載せる: 走りを su 伸縮・層を α 傾ける(0.283/0.450 ⇒ N=9・su 0.988・α 7.7°)。⛔ 石段の勾配 32° で剪断すると石が倒れて見える。
- bisect の補間で ±x の頂点が 1e-9 ずれ、左右対称の検算が丸めの境で落ちる ⇒ 1e-6 へ寄せる。

**Why:** 本線の打込接ぎと肌を合わせる【硬】で、切石の布積みの a/b の作法は連続した写真の肌に効かない。
**How to apply:** 段ごとに並べる駒へ連続テクスチャを貼るときは `uchikomi_cycle` で N を決め、据え手へ i%N を伝える。関連 [[ishidan-sode-sheared-module]]
