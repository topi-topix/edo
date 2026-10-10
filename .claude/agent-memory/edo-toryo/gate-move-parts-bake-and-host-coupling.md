---
name: gate-move-parts-bake-and-host-coupling
description: 表門を別の辺へ移す巡(岡部 B 案 第101巡)の3つの止め ── 新造の門長屋の FBX が無い・planes[].fall(axis/hiAt 形)を graded が焼かない・腰石垣と門の内の下水が gate.host を「N39_0」として読む
metadata:
  type: project
---
2026-10-10 EDO-0502 第101巡(表門を辺39→辺40)。流す前に止めて返した。

1. **欄の asset が「新造」なら、流す前に FBX を ls する**。`Own.NagayaOmoteMon(14.544, 10.0, true)` も N40_1 の `NagayaOmote2F(14.803)` も焼かれていなかった。
   PlaceOmoteNagaya は 1 本目に欄どおりの版(mon10)を置いてから向き(sSign)で gc を出し直し `_kutai` を引く ⇒ 欄の版と _kutai の版(N39_0 の前例では gc = len − 欄の値・14.54 なら mon4.54)の両方が要る。
2. **`planes[].fall` は `{axis, hiAt, yHi, yLo}` の形だと bake が読まない**(sashizu_lib は `fall.ramp` だけ)── 算出物の graded は Hokuto を一枚 13.22 で持ち、Stage1 はそれを写すだけ。graded を格子で刷ってから流す。
3. **`gate.host` を「門のある棟」以外の意味で読む関数**: RoadEdgePlanOf(腰石垣・門の口の踏み段)・OmoteGesuiPlan(門の内の下水)・背の雨落ちの下流(EdgePt(gate.s))。
   host が辺40 へ移ると腰石垣が辺40 へ行き、さらに roadEdge の文から「踏面 … を狙う」が消えたので RoadEdgePlanOf は「読めない」で**黙って全部退く**。
   直すには腰石垣の棟を roadEdge の文の名指し(N39_0)から取り、口が無い棟では ps0/ps1 と踏み段を外す(ps0/ps1 は 10 か所以上で使う)。

How to apply: 門・棟の欄が動く巡は、①新造の FBX の有無 ②graded を格子で刷る ③`Get(D, "gate")` を grep して host の意味を確かめる、の3つを Unity を流す前に。関連: [[return-lost-when-sashizu-text-format-changes]] [[nagaya-mon-gate-offset-axis]]
