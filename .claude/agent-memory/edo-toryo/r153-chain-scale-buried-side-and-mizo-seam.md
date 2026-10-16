---
name: r153-chain-scale-buried-side-and-mizo-seam
description: 岡部 第153巡 — 台の倍率を一続きで揃えると座の低い棟(N18_0)の台が全部「埋まり退けた」になり、浅い出隅 P19 が偽の「留めの版が要る」を出す・溝の継ぎ目の節点は上に被る土留めで取り残しから漏れる・桝の尻の溝は棟の走りの終わりで止まり桝まで 4.3m 開く
metadata:
  type: project
---
2026-10-17 EDO-0502 第153巡(PlaceIshigaki の一続きの倍率・EdoBuild.FillConvexCornerSlits・EdoBuild.LowerStrandedNodes・前の下水溝 drains.route の尻)。

1. **揃えた倍率で片側の台が消える**: N18_0 の座 17.60 は辺18 の全長で地表(17.67〜18.36)の下 ⇒ 倍率 1.0 の台は全部「埋まり退けた」。CastleSec は残るので
   FillConvexCornerSlits が P19 を「端の駒が見つからない」⇒ MiterBaseWait(部材方への版の頼み)に入れていた。相手が居ないので版は要らない ⇒ 区間の駒が 0 なら ℹ で待ちに入れない。
2. **溝の中の土の最悪 0.84 @(-456.5,944.0) は継ぎ目ではなかった**: mizoParts の二度目の判じ(溝の継ぎ目で上に土留めが被る節点 15)を入れても最悪は動かず(180→177)。
   UserData/Backups/Okabe/soil_over_faces.tsv で名指すと溝の頭の駒 D_MinamiHei_w_000 の床の上(地表 19.65・床 18.81)で、隣の TW_Minami_Mizo_0_14_008f の見え面にも土 1.55。
   溝の頭が土留めの法の下へ入る所 ⇒ 下げの手が最初に当たる面(土留めの法)で止まる型(推定・未確認)。次は SinkGroundUnderMizo の光線を溝の駒だけで打つ所を測る。
   検めの tsv(F=見え面・M=溝の床、x z 面 土の厚み)で先に名指してから直す。
3. **D_N39_1_Mae_012 の小口の隙 0.45**: 溝の尻を `min(区間の終わり=N39_1 の躯体の走りの終わり, 桝の口の面)` で止めていた ⇒ 角の手前に別 run の棟(N39_k 4.2m)が挟まって 4.3m 手前で終わった。
   桝の尻の溝は桝の口の面まで延ばす。

**How to apply:** 倍率・控えを動かす巡は S1+S2(20 秒〜1 分)で tome.txt の WAIT と「建てない」を数えてから 2b。WAIT が出たら相手の区間の駒の有無を先に見る。
光線で「真上に駒が在るか」を見る判じは、上に別の駒が被る所(溝×土留め)で必ず漏れる ── 判じる相手の駒の組を名指す。
関連 [[r152-nagaya-base-chain-and-foot-fill-corner]] [[r148-stranded-nodes-and-embed-count]]
