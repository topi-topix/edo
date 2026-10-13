---
name: r130-grade-qa-frames-g0-hei-feet
description: 岡部 第130巡 ── S3d を単独で(reload の後に)流すと地形が 5262 節点・±2.2m 変わる・造成QA の「最大の差の Stage」帰属は S1 に寄る(段ごとの値を並べて読む)・池の岸は QA の枠に無かった・GroundQA の C は囲い・台の石の下を地面と読む・塀の足の浮き 0.9/0.65 は段の下の駒が閉じる
metadata:
  type: project
---
2026-10-14 EDO-0502 第130巡。

1. **S3d を domain reload の後に単独で流すと、S1→S3d を一続きに流した終わりと地形が 5262 節点・±2.2m 違う**(NW の段の塀の足 x−628〜−644 に造成QA の超過 25 升が新しく出た)。
   S3d は S2/S2b が static に残す物(_sideEndBenches・_heiFootLines ほか)を読む。⇒ 外周の地形を書き直したら **S1 から一続き**で流す。造成QA も一続きの中で測る
   (同じ GradeQA が reload 直後は 238・別の検査の後は 59 ── 小段の枠 SodeBenches が _sideEndBenches に依る)。
2. chain の帰属(各升で |dh| 最大の Stage)は S1 が全面を書き直すので **全部 S1 に寄る**。⇒ 升ごとに pre/S1/S2/S2b/S3/S3d の値を並べる(r130/d2.py・d3.py の型)。
   134 升のうち 98 升は S3d の池の岸の断面(PondBankToTerrain・岸 21.00)が設計面 20.20 を 0.80 上回っただけ ⇒ GradeQA に池の岸の枠(PondBankDesign を設計面の上で引く)を足した。
3. **GroundQA(SkinGapTable)の C は、外の点が囲い(Kakoi)・段に接しない石垣(台の石)の中に落ちると、その下で下げた地形を地表と読む**(parts に入らない駒は覆いに数えない)。
   G0 の 1.89 は N12_0 の台の石 IG_N12_0 の中・m00 の 0.87 は S_Hei_06 の塀の足の中。⇒ 検査の側の話(普請奉行へ返した)。
4. G0 の「N12_0 の妻から 0.3 以上【硬】」は辺の端からの道のりで読んでいた ── 実の躯体の足(EdoBuild.BodyFootHullXZ)と桝の外の面(MasuOuterHull)の離れで測る EdoBuild.MasuLowestClear に替えたら、
   溝の芯を内面 +1.05 へ寄せた(innerDitch)ので辺11 のどこでも離れ 0.07 しか取れず **建たない**(硬)。⇒ 指図の二つの硬が両立しない ── 裁定へ。
5. 塀の足の浮き(普請検査の hei2: 足の頂点の真下を石垣の石だけで測る)の 0.909 NW_Hei_1_TomeA・0.648 S_Hei_18_0_TomeB は、上の段の棟止めの足の隅の頂点が下の段の台の天端の上へ出ている一点。
   下の段の塀の躯体の面がその下を閉じ、内外の近景(r130_h1c_*・h2c_*)で隙は見えない。0.202 N_Hei_26_1_4 も一点・写真で隙なし。
6. 部材方が流しの最中に EdoAssets.cs をコミットした ⇒ 次の execute_code が「アセンブリが古い」で止まる。compile_wait を打ってから続ける(新しい AH_Ago は版の検めで自動で採られる)。
**How to apply:** 外周を直したら S1→S2→S2b→S3→S3d を一つの execute_code で・測りも同じ中で。GradeQA の大きな塊は段ごとの値で「誰が書いたか」を読み、設計の別の工事なら枠を足す。
関連 [[r129-grade-seroji-hakiguchi-chain-s3]] [[okabe-perimeter-rerun-order-and-neribei-measure]] [[qa-misreads-stack-and-single-mesh-gate]]
