---
name: kado-short-arm-and-foot-groove
description: 隅の腕を袖の実測から焼いた組で選ぶ(KadoShortArm)・野面の足元の溝は皮の cap が足の石の頭まで掘っていた・凸包の中の空きの点は底を持たず塞がれない・袖の背の包絡は踏面より下も見える
metadata:
  type: project
---

2026-09-26 EDO-0437 第6巡(山王)。

1. **隅の腕は `EdoBuild.KadoShortArm` が選ぶ**(PlaceRunCorners に abut=石段の袖・armPathOf=IshigakiKado(4引数))。要る長さ = 腕の体
   (控えの線〜法の面・留めの二等分線で分ける)へ入る相手の頂点の走りの最小 と 区間の開いた端。焼いた組は素の隅のフォルダを `_A*` で引く。
   ⚠ 袖は Kaidan が建て、Dodome の後段(AbutStairsToWalls)で端を詰める ── 腕は**詰めた後の袖**で測った値。Kaidan から流すと詰める前の袖で測る。
2. **前庭の東の野面の足元の溝の筋(深さ 0.2〜0.25・前 0.2〜0.8m)** = 皮の cap の Floor が、法の足の石の上向きの小面(13.59)を
   「地盤 − 石 ≤ 2×帯」なので天端扱いで掘っていた。近くの天端(CrestAround)より地盤が帯を超えて低ければ根入れ ⇒ 地盤で止める。
3. **打ち切りの駒の端で天端の石だけ張り出す所**は、凸包の中でも真上・真下に面が無い点(空き)。sealFace が rr=0 で底を引けず、
   石の下が 0.02〜0.04 覗いた ⇒ 空きの点は外と同じに近くの底で塞ぐ。
4. 袖の背の包絡(MeasureSodeBackEnvelope)は踏面の上だけ打っていた。見え面の外の地表が踏面より 1.8m 低い所では下の背が隅へ 0.035 入る ⇒ visAt を渡し底から打つ。
5. レンダの「天端の四角い抜け」は野面の駒(H0900_d・H0600_b)の天端の石の欠けで、芯の Danishi 面と皮が覗く ── 部材の話。

**How to apply:** 野面・土留めの足元の筋は、まず見え面に直交する断面で描かれた地表を 0.2 刻みで引き、駒の上向きの面の高さと並べる。
関連: [[nozura-wall-traps]] [[run-corners-seams-and-tiers]] [[parity-inside-test-false-intrusion]]
