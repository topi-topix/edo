---
name: r145-facestraight-pca-tilt-and-corner-road
description: 岡部 第145巡 ── FaceStraight の向きは頂点の主軸で、端を留めて切った長屋で 3.26° 傾く(P12 の練塀の斜めの駒が 63.72° を引き焼いていないで退く)・区画の外の「説明の無い」81 節点は cornerR137b の角の前の道の 1/50
metadata:
  type: project
---
2026-10-16 EDO-0502 第145巡。

1. **症状**: N12_0 が留めの版(mc0x115)で建った途端、S_Hei_08 の終わりが「Neribei_Naname_637_S は焼いていない(角 63.72°)── 従来の端」で退き、
   S_Hei_08_0_1 の足が石の上で 0.795 浮いたまま。辺11×辺12 の真の角は 66.97°(parcels.json)・N12_0 の yaw 183.536 も辺12 と一致。
   **原因**: `EdoBuild.FaceStraight`(EdoBuildMizo.cs)→ `WallFaceLine` の向きが**頂点の主軸(PCA)**。片端だけ斜めに切った駒は頂点が偏り、主軸が 3.26° 傾く。
   **直し(未保存・スワップ超過で止めた)**: 向きを帯の頂点の凸包の、面の側の最も長い辺で取る。案は scratchpad r145/facestraight_new.cs。
   当たる先: 土井 D7/D9/D10/N7 の FaceStraight(対称な駒では不変の筈)・NeribeiNanameEnd(岡部 P12)。
2. **区画の外の説明の無い 81 節点(最大 0.130)** は S3d の `FallAwayFrom`(cornerR137b「桝の天端 −0.02 から道へ 1/50」)── 書き手は 84 節点・最大 0.131 と一致。
   仕分けの器(chainB の c_out2)に cornerR137b の面が入っていないだけ。段ごとの bin の差で S3→S3d のみと割れた。
3. スワップは S2b の終わり(09:00 頃)に 2.9→12.4GB へ跳ねた。S2b は 38 分。

**How to apply:** 「相手の面の向き」を測る器を新しい版(斜めに切った・非対称)に当てる時は、主軸でなく面そのもの(凸包の辺)で向きを取る。
区画の外の仕分けは指図の書く欄(cornerR137b)も「指図の道の面」に入れる。関連 [[r144-both-end-miter-residual-and-outside-terrain]] [[p12-naname-end-and-michi-cut-r128]]
