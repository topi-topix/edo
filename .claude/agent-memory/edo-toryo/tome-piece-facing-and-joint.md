---
name: tome-piece-facing-and-joint
description: 野面の積み止めの駒は FaceWallToLine で 180° 回る(奥行>走り)・継ぎ手を全頂点の Contact で測ると小口の裏の石で 0.2 押し出す・ToeBenchOf に渡すと盛を 2.55 切る
metadata:
  type: project
---
2026-10-07 EDO-0502 第43巡(岡部 ③ の端を積み止め Sanno_Nozura_H*_Tome{P,M} で終える・EdoBuild.PlaceNozuraTome)。

1. **FaceWallToLine は積み止めの駒を裏返す**: 走り 0.909 に対し小口の面の奥行 1.818(全体 Z 2.3)なので FaceSide が向きを取り違え、M の 2 駒を
   芯で 180° 回した(小口が逆の端へ)。⇒ 天端の帯の前の縁の射影だけで線へ寄せる(回さない)。yaw は X=(fN.y,−fN.x)、小口が away なら P・逆なら M。
2. **継ぎ手を全頂点の ContactPts で測ると、小口の面の裏の石(u≈−0.3〜−0.7)が隣の駒の背の石と同じ筋に入り −0.2 の偽のめり込み** ⇒ 外へ 0.2 押し出した。
   ⇒ 双方とも端の点から run−0.3 より内の頂点だけで測る。
3. **ToeBenchOf に積み止めを渡すと控えの後端が 1.16→2.76 に伸び、背の縁の帯が積み止めだけを拾って天端を 1.5 低く読み、盛を最大 2.55 切った**
   (二巡目の Stage2b で発覚・岡部 辺24。地形は退避 hm_pre_r43.bin から 42 節点を戻した)。⇒ 背の小段・裏込めの測りは名に "_tome" の駒を除く。
   積み止めを足したら次の Stage2b の「控えの後端」「天端 a→b」を前の巡のログと diff する。
4. 返しの重ねた run(#ret*_1)は計画の段では near が偽でも、据えの段で上の run の駒を「近くの駒」と拾って端を 0.49 へ縮め駒 0 になっていた。
   積み止めの端は through にして近くの駒への突き付けを使わない。

関連: [[slope-sode-flat-kado-and-end-specs]] [[nozura-end-rule-blocked-by-back-soil]]
