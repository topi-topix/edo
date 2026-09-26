---
name: crest-of-other-and-step-yield
description: 上の段の法の足が下の段の天端に載る所で皮が天端と同じ高さに張り付く(TopIndex.Top が別の駒の天端を見ない)・段石の端に被る隅石は段の外へ退ける(YieldWallsToSteps)・MeshInside は二つ同時に生かさない
metadata:
  type: project
---

2026-09-26 EDO-0437 第9巡(山王)。

1. **皮が天端に被る 2 点(TW_Gusho_N_001f・28.300)** = 透塀の土台 TW_Koshi_S の法の足が御供所の郭の北の土留めの天端に平面で重なる所。
   TopIndex.Top は最も高い上向きの面の駒(Koshi)だけで帯を篩い「法の面」(faceTop)と読み、皮の cap の下限 Floor が足元の面
   (28.30 = 下の駒の天端)を返して皮の節点が天端と同値になった。⇒ `TopIndex.CrestOfOther`(同じ点の別の駒の天端を拾う)。
   皮の節点の値を直に読む(EdgeSkin_Sanno の頂点)と一目で分かる。
2. **段石の端に被る隅石・野面** は `EdoBuild.YieldWallsToSteps`(段の幅の向きへ駒を平行に退ける・見える所だけ・上限 0.15)。
3. **MeshInside は層 31 の一時の当たり** ── 二つ同時に生かすと光線が両方に当たり内外を誤る。一つずつ作って捨てる。
4. 指図が他の窓で直されると RunFrom が「算出物が焼かれていない」で 3 秒で止まる ⇒ `bake_impl.py sanno --write`(乾いた試しは 2 分超・直に --write)。

**How to apply:** 皮の被りは「どの駒の上向きの面が最高か」を先に引く。段と土留めの重なりは段を動かさず駒の側で。
関連: [[kado-short-arm-and-foot-groove]] [[post-board-run-and-mesh-inside]] [[parity-inside-test-false-intrusion]]
