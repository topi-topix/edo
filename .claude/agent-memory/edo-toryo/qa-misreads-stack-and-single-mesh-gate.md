---
name: qa-misreads-stack-and-single-mesh-gate
description: 検査の「浮き・子0」は測り方の読み違いのことがある ── 積みの石を地表で測る・一体の門の子0・皮の前に格子で据えた垣。直す前に当たりの相手を揃えて測り直す
metadata:
  type: project
---

2026-10-04 EDO-0502 第15巡(岡部)で、検査の上げた 5 件のうち 2 件は測り方の読み違いだった。

- **石段の最下の積みが地表から 0.075〜0.49 浮く** ── 検査は積み(*_tsumiN)を全部**地表**で測っていた。上の段の積みは一段下の積みに載るので地表からは浮いて見える。
  一段下の積み ∪ 描かれた地表 で測ると全部 +0.009 以下・最下は地表へ根入れ(0.005〜0.78)。⇒ 積みは「下の駒+地表」の床(EdoBuild.Bed)で測る。
- **通用門 Tsuyomon の子 0** ── Munamon_2.73.fbx は一体のメッシュ(サブメッシュ 5)なので子が無いのが正常。建っている(接地 −0.014)。
  門の完備の検査(EdoGateComplete.Run)は gate/komon の `plan.monW/monD` を読む ── komon には plan が無いので「未検査」。要るのは指図の欄。
- **天端の垣の柱が +0.050 浮く** ── 垣は Stage2b(皮の前)に 2m 格子で据わる。格子は土留めの天端より 0.2 高い所がある。
  皮の後に据わる床で据え直す(EdoBuild.ReseatCrestFence・Stage3b の末)。同じ据え直しで Hokuto_6_post の 1.83m の埋まりも解けた。

**How to apply:** 浮き・埋まりの指摘は、まず「その駒が触れる相手」(下の駒・天端・皮)を床に入れて測り直す。皮の前に据わる物(垣・坂の縁)は皮の後に据え直す段を Stage3b の末に置く。
⚠ 残り: 垣の駒が段の境を跨ぐと足の三点の一つが 0.42〜0.44 空く(Hokuto_4_004・5_011)── ContactOn の最小では捕まらない。
⚠ delayCall は execute_code から発火しない ── EditorApplication.update に一度だけの callback を足し、QueuePlayerLoopUpdate を軽い呼び出しで打って起こす。
関連: [[contact-must-use-drawn-surface]] [[long-run-guard-and-soft-only-converge]] [[nozura-dan-piece-fixed-height]]
