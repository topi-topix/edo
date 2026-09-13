# 地形編集 — 造成・穴埋め・ベイク範囲・水際の不整合

## Modern-DEM pit repair & rotated-grid terrace grading (proven 2026-08-02, 松平大和守邸)

- **近代DEMの掘削穴（ビル基礎跡等）はラプラシアン緩和で埋める**: bbox内の「h < しきい値」セルだけを
  可変にし、周辺の正常セルを境界条件に `h = 4近傍平均` を600〜1200回。等高線が周辺と連続する
  自然な鞍部になる。しきい値判定はポリゴン内外を問わず適用しないと、盛土リム帯(d<3で自然地盤
  維持)の内側に深い溝スリバーが残る（実際に残った）。
- **回転グリッドの段差アーティファクト**: テラス段差(6-8m)の遷移帯を2mハイトマップに書くと、
  壁線がグリッド斜め横断のとき ±(cell·(|sinθ|+|cosθ|))/2 ≈ ±1.4m の階段ジグザグが出る。
  2.4m厚の壁では隠れない → 4.8m厚（護岸規格）で覆う。詳細は unity-modular-stonewall §14。
- **ブックマーク画角→ワールド変換**: bookmarks.json の pos/euler/fov/aspect から一時カメラを
  作り `ViewportPointToRay(nx, 1-ny)`（マークは左上原点）→ 地形と二分法で交点。古地図オーバーレイ
  を SetActive して同画角で撮り直すと、マークと切絵図の区画線の一致を1枚で検証できる。
  区画ポリゴンの視覚検証は「マーク=赤球・ポリゴン辺=緑球列を overlayY+2 に浮かべて正射で撮る」。

---

## 複数区画の段丘一括造成(三屋敷再編 2026-08-08 で実証)

ブロック内の複数敷地を一度の SetHeights で造成するパターン:
`target = 区画毎の関数` を1セルずつ評価する。構成要素は
①区画ポリゴン(石垣runのPCAラインフィット交点) ②テラス関数(基準壁からの符号付き距離 dE のバンド+lerp)
③庭園コア多角形の blend(w3 = 内側1、外へ12mで0 — 池・既存庭を上位テラスに固定)
④壁際上限 min(target, coping-0.3)(壁から4..12mでフェード) ⑤池保護矩形は continue で完全不変
⑥自然地形の温存は t3 = max(パッド, min(現況, キャップ)) — 築山や起伏を潰さない。
落とし穴2件: (a)隣接パッドの境界遷移(±2セル)は共有壁の体(2.4m)からはみ出す → 低地側 d∈[1,9]m を
lower-only で切る後処理が要る。(b)接地の一括パスは水面上に bounds.center を持つ護岸・橋を池底へ
引き込む(unity-buke-yashiki §14 参照、gitシーンからの復元手順つき)。
スプラットの門前白洲・蔵前土場は「max合成→正規化」のディスク塗り(Perlin 0.13周波でエッジ揺らし)で十分。

## ベイクは「範囲限定」を既定にする(2026-08-09の事故で確立)

土地利用ベイク(`EdoLandUse.Bake`)がスプラット全面を塗り直すため、ユーザーがテレインペイントで
手描きした泥/草(約27000セル=2.5%)が2度消えた。**手描きは常に存在すると仮定する**。

- **Undoは効かない。** スプラットの実体は `TerrainData` ではなく `terrainData.alphamapTextures`
  (Texture2D[])。`Undo.RegisterCompleteObjectUndo(td, ...)` だけでは Ctrl+Z しても地面の塗りは
  戻らない(高さも同様)。両方登録すること:
  `Undo.RegisterCompleteObjectUndo(td.alphamapTextures, name)` ＋ `(td, name)`。
  ディテール(草)は td 側に載るので td 登録で戻る。
- **範囲マスク方式**: `map = td.GetAlphamaps(...)` を**既存値から開始**し、
  `cov = Coverage(wx,wz)`(0..1、境界はフェザー)で `Mathf.Lerp(既存, 新規, cov)`。`cov<=0.001` は
  `continue`。走査は範囲のバウンディングボックスに絞る(4096²のディテール格子を全走査すると重い)。
  ディテールも同様に `GetDetailLayer` から開始し、範囲内だけ 0 クリア→再生成。
- **範囲の与え方**は2つ用意すると実用的: ①ブラシが記録している塗り跡(座標+半径)の和集合＝
  「塗った所だけBake」 ②選択オブジェクトの Renderer bounds + マージン＝「範囲ベイク」。
- **自動バックアップ**: ベイク直前にスプラットを `TerrainBackups/splat_<stamp>.png`
  (4層→RGBA、Assets外に置いてimportさせない、.gitignore)に保存し、復元メニューを用意する。
  8bit量子化＋復元時に再正規化するが、事故復帰用としては十分。
- **全面ベイクのメニュー名に危険性を書く**。「ベイク(自動＋上書き)」のような無害な名前だと誤爆する。
  `EditorUtility.DisplayDialog` で確認を挟む。
- **検証手順**: 遠方の未着色域に試験パッチを人工的に塗る → その一部だけを覆う矩形で範囲ベイク →
  ①パッチの覆われた側が自動値に戻る ②覆われていない側は残る ③**パッチ外の差分が0**
  の3点を数値で確認する。目視では漏れを見逃す。
- **復元の掘り出し口**: 大きな .asset が git-lfs 管理なら、直前コミットの実体が
  `.git/lfs/objects/<xx>/<yy>/<oid>` に残っている。Assets 配下にコピーすれば Unity が
  TerrainData としてimportするので、**スプラットだけ**(高さ・木はそのまま)差し戻せる。

---

## 8b. WaterBody "gap at the shoreline" after the Bank Smooth brush

Symptom: after gentling a pond/moat bank with `EdoBankSmoothBrush`, a **gap appears at the waterline** —
the flat water plane's edge floats in the air with ground visibly lower just outside it. Diagnosis that
nails it (no eyeballing): for each `WaterBody.outline` vertex sample `terrain.SampleHeight+ty` AT the
vertex and a few m OUTSIDE it (march along the edge **normal**, NOT vertex-minus-centroid — a meandering
river's centroid gives a wrong "outward"), count how many are `< wb.waterY`. Many below = the water
surface sits *above* the surrounding land = floating edge. Cause: the brush **averages** the bank height
toward the dug basin floor, dragging the shore below `waterY`.

Two traps make the obvious fixes fail:
- **"🌊 水位を地形に合わせる" (FitToTerrain) can't fix it**, because the Bank Smooth brush's `UpdateSnapshots`
  wrote the *lowered* heights into the WaterBody's pre-dig snapshot. Fit reads that snapshot, so the
  smoothed-away bank is now treated as "original terrain" and the lost height is unrecoverable that way.
  (`waterY` also stays pinned up by the interior-min term, so it keeps floating.)
- **Raising the banks back (`raiseBanks`+Recarve) works but DESTROYS the user's smoothing** — it rebuilds a
  lip just above the water exactly where they just gentled it. Don't reach for it if they *wanted* the
  gentle shore.

**Best fix — widen the water to the waterline (keeps water level AND the smoothing):** the smoothed bank is
now a gentle shelf dipping just under the surface. Instead of moving terrain, **move the water outline
outward** onto that shelf until it meets ground at `waterY`. For each vertex with `H(vertex) < waterY`,
march along its outward edge-normal to the first point where `H ≥ waterY+0.1`, set the vertex there, then
`WaterBaker.RebuildSurface(wb)` (surface mesh only — do NOT Recarve, which would re-flatten the shelf deep
and undo the smoothing; terrain is left untouched). The widened strip becomes natural shallow shore.
On the edo river this needed only ≤4 m of outward move per vertex (68/99 verts), and drove
"verts below water at/outside rim" from 68/43 → 0/0. Register `Undo.RecordObject(wb)` so it's revertable;
verify by re-running the same below-water count, not by pixels (the seam is subtle at distance).
