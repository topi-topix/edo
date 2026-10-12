---
name: graded-bin-stale-after-sashizu-commit
description: 岡部の指図を書き換えた直後は okabe_graded.bin が古く S1 が黙って算出物の 1m で造成する(⚠ 1行だけ)・焼き直しても静的な _graded が残る・隅の座は算出物が古い
metadata:
  type: project
---
2026-10-12 EDO-0502 第119巡。

1. **症状**: S1 のログ 3 行目が「⚠ 0.25m の造成の面が古い指図から焼かれている ── 算出物の 1m で造成」。下げ最大が 2.01→3.16 と変わる。
   **原因**: GradedBin() は bin の頭の sha256 を今の指図と比べ、違えば 1m の impl へ落ちる。指図のコミット(普請奉行)は bin を焼き直さない。
   さらに `_graded` は静的に掴むので、bin を焼き直しても同じドメインでは 1m のまま。
   **対処**: 流す前に `python3 Tools/Sashizu/impl_okabe.py --graded-bin`(80 秒)→ `_graded` を null(reflection)か compile_wait の後に S1。
   S1 のログの 3 行目が「造成の面 docs/Sashizu/okabe_graded.bin(1330×706・0.25m)」であることを見る。bin は C# と同じコミットへ。
2. 算出物の corners[].seat は前の地形で焼いた値で、隅が隣の直線より 1.14 低い/0.45 浮いた ⇒ SeatKadoToRuns(直線の駒の底の低い方)で据え直す。
3. 一枚物の練塀の隅を KadoFace の素の版で寄せると腰の笠(ishigaki)を外面と読み直線と 0.09 ずれ、入隅(P7)は相手の腕の根元を拾い 0.69 ずれた ⇒ 壁面の篩+二等分の線の版。
4. TW_Higashi_Minami(案A): kado6 の西の腕は TW_Higashi_Se に直交 = 東西から 5.7° 振れ、西へ 40m で練塀へ 4m 寄る ⇒ lineCheck +2.4 を西 23m で割る(西端 +0.2)。

5. 足の下の地面を上げる FillUnderFoot: 一枚物の練塀は**底の面が無い**(下から光線を打っても 0 節点)⇒ 足の頂点の凸包で測る。
   縁の一升を上限なしで上げると、外が急に落ちる所(P24 の外・基壇の端)に幅 0.25・高さ 2m の土の柱が立った ⇒ 縁は +0.10 まで・石の駒の下は触らない・控えを書いて次の 3d の頭で戻す。

**How to apply:** 指図のコミットの後の最初の S1 は bin を焼き直してから。隅の座・横ずれは joint 測り(scratchpad r119/joint_s2b.txt の型)で 25 基を見る。
関連 [[okabe-perimeter-rerun-order-and-neribei-measure]] [[stale-impl-after-parcel-redraw]]
