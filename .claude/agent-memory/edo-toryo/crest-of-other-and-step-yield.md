---
name: crest-of-other-and-step-yield
description: 天端の面の重なりは別の駒が真上を覆えば見えない(数え方の話)・段石の端に被る隅石は段の外へ退ける(YieldWallsToSteps)・MeshInside は二つ同時に生かさない
metadata:
  type: project
---

2026-09-26 EDO-0437 第9巡(山王)。

1. **皮が天端に被る 2 点(TW_Gusho_N_001f・28.300)** は、透塀の土台 TW_Koshi_S_000f(天端 28.65)が平面で真上を覆う所の皮で見えない。
   ⇒ 直したのは数え方(TuckUnderCrest の面の重なりから、別の駒の天端が覆う点を外す)。皮の節点の値と、その点の最も高い駒(TopIndex.TopRaw)を先に引くと早い。
2. **段石の端に被る隅石・野面** は `EdoBuild.YieldWallsToSteps`(段の幅の向きへ駒を平行に退ける・見える所だけ・上限 0.15)。
2b. ⚠ 退けると段の端の口が開く: 野面の返し Kiri_012f/027f を 0.086 退けたら最上段 Dan_04 の端の口が 0.14〜0.24。めり込みと隙はどちらも許容0 ── 石の出入りの大きい野面は段の端を石へ切る駒(部材)の話。上の段の控えは「他の段の中」で外す(帯で切ると最上段の端の見える脇を落とす)。
3. **MeshInside は層 31 の一時の当たり** ── 二つ同時に生かすと光線が両方に当たり内外を誤る。一つずつ作って捨てる。
4. 指図が他の窓で直されると RunFrom が「算出物が焼かれていない」で 3 秒で止まる ⇒ `bake_impl.py sanno --write`(乾いた試しは 2 分超・直に --write)。

**How to apply:** 皮の被りは「どの駒の上向きの面が最高か」を先に引く。段と土留めの重なりは段を動かさず駒の側で。
関連: [[kado-short-arm-and-foot-groove]] [[post-board-run-and-mesh-inside]] [[parity-inside-test-false-intrusion]]
