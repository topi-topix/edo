---
name: koguchi-cover-capped-by-rounded-shoulder
description: 小口の土を盛っても描かれた地表が 0.16〜0.19 足りない正体は、皮の「天端の下」の cap(自分の点の天端 − 0.15)が野面の丸い肩で小口の際の点を下げること
metadata:
  type: project
---
2026-10-08 EDO-0502 第51巡(岡部 TW_Kado_Sode_0_0_016f の小口・頂 16.65)。
症状: 設計の地盤の節点を 16.70 へ盛っても(hold)、小口の前 0.02 の描かれた地表が 16.47〜16.49。SkinTrace で追うと、際の皮の点(外形の中・near 2)は
HoldY で 16.51 まで上がった後、「天端の下(self 16.56 cap 16.41)」で 16.41 へ下げられていた ── 自分の点の天端は野面の丸い肩(小口の頂より 0.1 低い)。
もう一つ: 角の点は HoldY の双一次に立てていない節点(駒の幅の外・面より奥)が混ざり 16.51 止まり。
対処: hold の点は cap を「近くの駒の天端 − 0.05」まで緩める(CutEdgeSkin・CrestNear)・広げた帯は小口の面の奥へ 1 格子回り込む(Stage3b の小口の土)。
**How to apply:** 皮で何かを盛って描き切れないときは、まず SkinTrace で点を追い、どの手(cap・3b〜4)が下げたかを名指しする。頂点の格子 0.25 と石の丸い肩の差が効く。
関連: [[sode-check-skinground-and-dropped-run-residue]]
