---
name: lowpoly-vertex-window-empty
description: 低ポリの駒(階段廊下の踏板・側桁・高欄)を「頂点の窓」で測ると窓の内が空になり、回しを誤る・端が突き付かない。材で採るか光線で測る
metadata:
  type: project
---
症状(2026-10-04 EDO-0533 土井): ① 階段廊下 KaidanRoka が回し 0° を選び「走り 1.818(欄 5.454)・落差 1.502(欄 0.45)」(報告は ⭕ のまま)。
② 奥の塀の端 EndToFace が「L_HiromaOku の面が線の先に測れない(点なし)」。
原因: 踏板は箱で頂点が幅の端 ±0.729/±0.909 にしか無く、幅の内 ±0.709 の窓は空(90/270° は 0 点 → 候補から落ちた)。
塀の線の前 ±0.3m の帯も、側桁・高欄・柱の頂点は端にしか無く空。
対処: ① 段は材 "floor"(踏板のサブメッシュ)で採る(EdoBuild.BodyOfMat)。低い踏板の天端 = 上の床 − 落差で据える。
② 端は EdoBuild.ReachToBodies(三角形への光線)で測る。どちらも EdoGotenKit.KaidanRoka / EdoBuild.EndToFace に入れた。
罠2: 階段廊下の地盤を廊下の足形の中央値で採ると下の段(26.30)を拾い 0.45 低く据わる ── 上の棟の足形で FaceY を取る。
関連: [[one-mesh-part-split-by-submesh]] [[run-end-at-opening]] [[contact-cells-miss-flat-faces]]
