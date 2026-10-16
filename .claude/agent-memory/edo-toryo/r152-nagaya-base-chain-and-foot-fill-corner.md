---
name: r152-nagaya-base-chain-and-foot-fill-corner
description: 岡部 第152巡 — 長屋の台の有無は一続きで判じる(N17_k は segs 空で台なし)・倍率を一続きで揃えると控え c が動き長屋 12 棟の留めの版が外れて建たない・足の下の埋めは頂点で近い辺の c だけ見ると高い台の法の前に土の柱
metadata:
  type: project
---
2026-10-16 EDO-0502 第152巡(EdoOkabeYashikiBuilder.PlaceIshigaki / NagayaBaseChains / Stage3d の FillUnderFoot / EdoBuild.FallAwayFrom)。

1. **台の途切れ**: NagayaBaseWhole は「segs が空の run は触らない」+「棟がシーンに無いと ★ で帰る」。PlaceIshigaki は S2 で3回呼ばれ、1・2回目は長屋より前(棟が無い)
   ⇒ 効くのは3回目(SeatHeiLineKado の後)だけ。N17_k は segs 空・thin だけ ⇒ 台なし(写真 P18 の右半分)。直し: 一続き(端が 0.6 以内で接する長屋の run)のどれかが台を持てば全長へ。
   「全体が埋まり退けた」が 47→80 に増えるのは正常(埋まった駒は見えない)。
2. **倍率を一続きで揃えると建たない**: 北 1.0・表 0.75 に揃えた試しで控え c が 0.25〜0.75 動き、長屋 12 棟(N12〜N18_k・N39_k・N40_0・N40_3・N41_0)が
   「要る版 … ⇒ 建てない」。倍率を変える巡は、先に部材方へ揃えた控えで焼いた留めの版を頼む(要る版の一覧は S2 の試しのログで取れる・S1+S2 は 20 秒)。
3. **足の下の土の柱(P12)**: FillUnderFoot の allowUnderFoot が「最も近い辺の c +0.05 より奥」で判じ、二つの台が出会う頂点で高い台(N12 野面 c 1.0)の法の前の節点を
   低い台の辺(c 0.75)の奥と読んで練塀の足の底 19.1 まで上げた。犯人は UserData/Backups/Okabe/hei_foot_fill.bin(i,j,new,old の記録)で名指せた。直し: 射影が辺の内の 3m 以内の辺すべての c で判じる。

**How to apply:** 地面の歯・柱の書き手は Backups/Okabe の *_fill/_sink/_band.bin を (i,j) で引けば一発。倍率・控えを動かす直しは S1+S2 だけ先に流して長屋の待ちを見てから S2b へ。
関連 [[r151-tome-len-plus-crest-setback]] [[r148-stranded-nodes-and-embed-count]]
