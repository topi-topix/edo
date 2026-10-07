---
name: strip-min-max-leaves-float-and-gate-seat-before-skin
description: 筋の底の最小−頭の最大で積みを上げると全部の筋で浮く・門構えは Stage2 の地形で据わり皮で埋まる・皮の穴の升でも上げない規則で段石の背が窪む
metadata:
  type: project
---
1. 症状: 縁 Curb_R_UraZaka_0_004f が下の積み 004f_tsumi0 から +0.013 浮いた(9点)。原因: StackDownAtNozuraSteps が筋ごとに「上の駒の底の最小 − 積む駒の頭の最大」を別々の所で取って引いた ── どの柱の隙よりも小さい値になる。対処: 0.1m の柱ごとの差の筋内最小 → 筋の最大(2026-10-07)。結果は全筋で触れ、他の筋は −0.025 の重なり(部材どうしのめり込み・数えない)。
2. 症状: 通用門 Tsuyomon が描かれた地表から −0.014 埋没。原因: SeatGamae は Stage2 で皮の前の地形(2m 格子)で当てる。対処: Stage3b 末で EdoBuild.SeatGamaeOn(描かれた地表)。
3. 症状: K_Dan1 の上がり口の段石の背が −0.16 窪む。原因: 返しの石垣の外形の中(near==2)は「外形の中の設計」が下げるだけで上げない ⇒ 地形 18.49 のまま。対処: 背の平らを SkinFace(TopLanding・tol 0.02)にすると「法の面の下」の規則が面の高さで描く。
**How to apply:** 積み・門・皮の上の平らの浮き/窪みは、まず「何で測って据えたか(格子か皮か・筋か柱か)」を疑う。皮の窪みは SkinTrace で規則の段を名指してから直す。
