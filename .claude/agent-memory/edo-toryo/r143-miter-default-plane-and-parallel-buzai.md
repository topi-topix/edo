---
name: r143-miter-default-plane-and-parallel-buzai
description: 岡部 第143巡 ── 出隅の留めを EdoBuild の既定へ(MiterPerimeterCorners)。控えの違う浅い折れは外面の線の交点が 4m 飛ぶ・門長屋の名の口は +X 端から・部材方が流しの最中に焼くと File.Exists だけの器が未 import の FBX で落ちる
metadata:
  type: project
---
2026-10-16 EDO-0502 第143巡(施主指示 2026-10-16「直角でない出隅は最初から留めて建てる」)。

1. **症状**: 留めの面を「二棟の札の外面の線の交点 Q」に取ると、岡部 頂点14(折れ 3.4°・控え 1.05 / 0.80)で Q が頂点から 4.3m 飛び、N14_0 の要る長さが 10.1 と出た。
   **原因**: 控えの差 δ の二本の線は浅い折れ θ で δ/sinθ 先で交わる。**対処**: 留めの面 = 角の二等分の線。通る点は Q が二等分の線から控え c 以内なら Q(角で段なく閉じる・頂点40/41)、
   それより遠ければ区画の頂点(外面は控えの差だけ段)── 部材方が焼いた長さ(15.98 / 17.63 / 17 / 19.4)と一致した。
2. **門長屋の留めの版の名の口(mon<gc>)は躯体の局所 +X 端から**(生成器の --gate は Blender の左 = Unity +X)。割りの −X 端からと読み違えて mon9.4 を探した。
   名の 0.01 の丸めで 0.01〜0.02 ずれる(N18_0 4.08 / 焼いた 4.07)⇒ ±0.05 で焼いた版を探し、口の芯は据えた後に実測(≤ 0.05)。
3. **部材方が流しの最中に FBX を焼いた**: PickMiterCut は File.Exists だけを見るので、.meta の無い FBX を「採れた」と返し Place が例外で S2 が途中で止まった
   ⇒ LoadAssetAtPath も見る。新しい FBX は EdoNagayaOmote.Remap()(触った物だけ再 import・18 秒)で材を結んでから流す。
4. 突き抜けを相手の札の front で比べると、相手の土台・一階の出(+0.03)や座の違い(19.2 / 19.0)を「突き抜け」と数える ⇒ 相手の同じ高さの外面(0.05 刻み)と比べ、帯は底〜BAND_HI 1.80。
   それでも座の違う入隅(頂点16)で土台が 0.005 前へ出る ── 座の違う二棟の継ぎは部材方の話。
5. 入隅の切った版は札の足で切った端と読めない(背が長くなる)⇒ SpecMiterCutEnds の照合は θ > 0 の端だけ。

**How to apply:** 外周の留めは EdoBuild.MiterPerimeterCorners に run を渡すだけ。「要る版」の待ちが出たら部材方へ名・θ・長さをそのまま渡す。
部材方が並行して焼いている巡は、流す前に Nagaya/ の新しい FBX と .meta を ls で見て Remap してから。関連 [[new-fbx-without-meta-reads-as-unbaked]] [[nagaya-mon-gate-offset-axis]] [[kadoarms-pivot-is-line-intersection]]
