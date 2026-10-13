---
name: face-front-columns-and-corner-slit-r126
description: 岡部 第126巡 ── 台の見え面の前の土の柱は PlaneBand の ext(辺の端の先)が隣の辺の見え面の前を上の座へ上げた物・P35 の出隅の口は天端 0.04 の差を「段の継ぎ目」と読んで両端を 0.27 引いた物・坂の端の駒を引いて高さを据え置き P22 で天端 0.098 低い・写真の柱は光線で名指す
metadata:
  type: project
---
2026-10-13 EDO-0502 第126巡(const.heiLine.faceFront【硬】)。

1. **見え面の前の土の柱(北 P35 の両脇)の正体は PlaneBand の ext**: 辺34 の帯を辺の端の先 1.5m へ延ばした所が、辺35 の見え面の前(線から 0.2〜0.8)に掛かり、
   上の座 23.6 で節点を上げた(周り 20.6)。cap(見え面の肩)は qCap = c−0.30 より奥しか見ないので止まらない ⇒ ext は他の辺の走りの内で q < q1 の節点を使わない。
   さらに最後に EdoBuild.LowerGroundBeforeFace(見え面の前の節点 → 区画の外の地表・見え面の下 → max(面−0.05, 外の地表))。
2. **写真の柱は光線で名指す**: shots.cs と同じ姿勢のカメラを targetTexture 付きで作り ScreenPointToRay(⚠ targetTexture 無しの pixelRect では画面の寸法で外れた)。
   石の駒へ一時の MeshCollider を付け RaycastAll ⇒ 地形が石より先に当たる点の sd。
3. **P35 の出隅の口(幅 0.5)の正体**: 22° の浅い出隅で両脇の頂点の天端が 0.04 違う(坂なりの区間は芯線の折れ点が頂点から 1.45 離れる)── PlaceCastleRun が
   1e-3 で「折れのある段の継ぎ目」と読み、高い方を頂点の先・低い方を 1.4 奥へ延ばし、③a が区画の外へ出た両端を引いて根石の端が頂点の 0.27 手前で止まった
   ⇒ EdoBuild.CORNER_STEP_MIN 0.10。浅い出隅は法で上へ V に開く(天端で 2c·sin(φ/2))⇒ EdoBuild.FillConvexCornerSlits が裏へ直線の駒を二等分の向きに据える。
4. **P22 の隙 0.059 の正体**: 12% 下りの短い区間(0.92m)の端の駒を ③a が 0.8 引いて高さを据え置き、天端が線より 0.098 低い ⇒ 引いた s × 勾配で y を直す。
5. S_Hei_08 s4.32 の 0.48 の浮き: 足の内の縁の節点(桝 G0 の縁の 0.05 手前)を FillUnderFoot が縁の上限 edgeCap 0.30 で止めた ⇒ rimFull に溝・桝の天端を足す。
6. 坂なりの run の帯で「段の脇の低い側」(前後 1.5 升の min)を全区間に掛けると、足の外の縁が勾配 × 0.375 浮く(0.01〜0.06)⇒ 段の点の脇だけ。
7. Stage3d 単独は流せない(compile の domain reload で _heiLineD・run.lineS が消える)── S1→S2→S2b→S3d の一続き。
**How to apply:** 見え面の前の土を見たら、まず「どの関数がその節点を書いたか」を ext・帯・足の上げで切り分ける(節点の高さ = 何の座か)。浅い出隅の石の口は天端の差を疑う。
関連 [[inner-ditch-and-foot-fill-r125]] [[kidan-crest-slope-r122]]
