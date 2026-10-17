---
name: r158-band-span-face-cap-gate-floor
description: 岡部 第158巡 — 犬走りの帯(PlaneBand)は辺の全長で引いていた(BandEdge.s0/s1)・内の帯は塀の下の石垣の見え面を埋める・出隅の扇が隣の台の見え面へ盛る(FaceAbove の上限)・門の口の床は誰も均していない(LevelGatePassage)・GK の桝の中を張り出しと読んで上げた・地面の書き手は Backups/Okabe の記録で名指す
metadata:
  type: project
---
2026-10-17 EDO-0502 第158巡(写真 r157 の土の欠陥 4 件)。

1. **土の壁(長屋 N39_0 の外面)= EdoBuild.PlaneBand が辺の全長**: run N_Hei_39 は辺39 の s 0〜5.45 だけなのに BandEdge.len = 辺の長さで帯を引き、腰石垣の天端と長屋の外面の間 0.25〜0.5 幅を座 17.46 へ上げた。
   BandEdge に s0/s1(run の走り)を足し、端の先 ext は範囲が辺の端に届く側(1.0m 以内)だけ。当たる先: 辺の一部だけを占める天端の線の run すべて。
2. **鋸の歯(頂点39 の内)= 内の帯(HeiLineBand)が塀の下の石垣 IGU_ の見え面を埋めた** ⇒ kidan「内…塀の下の石垣で受ける」の run は内の帯を引かない。
3. **二つの台の取り合いの土の塊(頂点19)= 出隅の扇 ext と FillUnderFoot の縁が隣の辺の台(IG_N18_0 の留め)の法の見え面の上へ盛った**
   ⇒ PartTops.FaceAbove(真上の一番上の面が法の見え面ならその高さ)−0.02 を上げの上限(PlaneBand/FillUnderFoot の upCap)。
4. **門の扉の下に土 = 門の通り口の床を均す手が無かった**(表門 N40_0 は平場で偶然 13.51)⇒ EdoBuild.LevelGatePassage(札の passage の局所 X × 壁体の下 1.0 の局所 Z を扉の下端へ)。
   扉の下端 17.90 = 座 18.0 − 0.10(長屋は全部 座 −0.10 で据わる)⇒ 指図の敷居 18.0 と 0.10 食い違う。
5. **GK の曲がり目の桝の中の土 = SinkGroundUnderMizo が肩の皮(xBody 0)で中の床まで「張り出しの下」と読み、床の上面 −0.03 へ上げた** ⇒ 真上が札の floor 以下なら桝の中(床の下面 −below)。
6. 写真の「板塀の台の足元の点々」は近くで撮ると地形の草(detail)── 土ではない。
7. 書き手の名指し: UserData/Backups/Okabe の band_*.txt(w/c 行 = i,j,高さ)と *.bin(名前+件数+[i,j,new,old] の正規化 ×49 −9.94)を (i,j) で引く型 = scratchpad r158 の who.py(x0 x1 z0 z1)。
8. S2b の関数名は Stage2b_Dan(TerraceWalls ではない)。

**How to apply:** 地面の歯・塊は who.py で書き手を名指してから直す。上げる手を足すときは upCap(FaceAbove)を渡す。
関連 [[r157-back-koshi-and-swap-after-3d]] [[r156-heiline-continuation-and-inner-wall]] [[r152-nagaya-base-chain-and-foot-fill-corner]]
