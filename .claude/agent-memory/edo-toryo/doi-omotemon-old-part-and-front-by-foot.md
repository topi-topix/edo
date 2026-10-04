---
name: doi-omotemon-old-part-and-front-by-foot
description: 土井の表門 Doi_Nagayamon.fbx は旧い版(躯体 11.18<11.82・番所が街路から見て右・扉口の切り下げ無し)・札の front は出格子を拾うので足元の外面で寄せる
metadata:
  type: project
---
2026-10-04 EDO-0533 S3 門(EdoDoiBuilder.Mon.cs)。
症状: 表門を口の芯 s=67.71 に据えると E13_N11 との躯体の隙 +0.322m・扉の下端が敷居より 0.80 高い・番所は北(s 72)に来た。
原因: 9/6 に焼いた旧い版 ── 呼び寸法 11.82 は破風込み(躯体 ±5.588)、`--gate-drop` 無し、番所/潜戸は局所 −X(Unity では外から見て**右**。作者は −X=左と書いた)。札も無い。
対処: 部材方へ差し戻し(躯体=呼び寸法・番所を局所 +X・gate-drop 0.80 の版)。S3 は KutaiOf で `Doi_Nagayamon_kutai.fbx` が出来れば自動で替わる。
罠2: 札の無い門を EdoPartSpec.Measure で測ると front = 出格子の前(+0.55)。外面の線へは **foot の +Z 最大**(土台の面)で寄せる(FootFront)。
罠3: Blender 直後の門長屋 FBX は材が素の knagayamap(白)。menu で全部 reimport せず、その FBX だけ AddRemap(knagaya01c.obj の材)+SaveAndReimport。
罠4: 指図の komon.s を S2 の後に直すと S2 の基壇の口が古い s のまま(−0.15)── S2 → S3 の順で流し直す。
関連: [[remap-menu-reimports-all-kado]] [[nagaya-mon-gate-offset-axis]]
