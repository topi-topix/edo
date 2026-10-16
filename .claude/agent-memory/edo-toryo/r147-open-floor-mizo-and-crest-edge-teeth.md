---
name: r147-open-floor-mizo-and-crest-edge-teeth
description: 岡部 第147巡 ── 型A_Ago の溝は底の裏の面が無く、下からの光線が抜けて溝の中の土が下がらない(全部の溝に鋸の土)・台の前の土の歯は天端の縁の節点(天端 −0.05)と見え面の前の節点の三角形・N40_0 の back の二つ目の書式が黙って退いていた
metadata:
  type: project
---
2026-10-16 EDO-0502 第147巡(施主の写真 r146_kado_P15・P40・P16)。

1. **溝の中の土(P40 の土の楔の正体)**: `SinkGroundUnderMizo`(EdoBuildChikei.cs)は第136巡から「真下から上へ光線を打ち最初に当たる下面」で下げる。
   Doi_Mizo_A_Ago は**底の板に裏の面が無く**、溝の中の節点は up-ray が抜けて「駒の下でない」で飛ばされていた(縁石の下だけ下がる)。
   ⇒ Mizo_Kita など全部の型A_Ago の溝の中に graded の土が残り、鋸の歯の土が溝を埋めていた(真上からの数え 6977 点)。D_N39_1_Mae_000〜002 では
   N39_0 の台の 1:1.5 の裾が溝の中に 1.4〜2.0 立ち、TW_Kado_Hokuto_2_0/kado1 に寄りかかる楔に見えた。直し: up-ray が抜けたら down-ray の面 −below。
2. **台の前の土の歯(P15)**: 天端に当たる節点は「天端 −0.05」、見え面の下の節点は前の地表へ ⇒ 0.25 格子の三角形が天端の縁の節点から前の低い節点へ斜めに下り、
   法の見え面より前へ出る(斜めの run と格子の向きの差で周期 0.8〜1.7m)。直し: `SinkGroundUnderParts` で天端の縁の節点を隣(8 方)の最も低い値へ(下限 = 駒の底 −below)。
3. 野面の継ぎ目の「前後 1.438(折れ 180°)」は路地を挟んで向き合う石垣の偽の対(kado1 × BackOfN39_1)── ang ≥150° を対にしない。
4. N40_0 の runs.back「s0〜8.18 は … 背の足元 座 −0.02 から 1/20 で擦り付け」は RunBackBands の正規表現に合わず黙って退いていた(148f の端の 0.51 の隙と N40_0 の背の浮き 0.23)。
5. 長屋の台は算出物 base[].thin(露出が薄い所)で途中が抜ける ⇒ NagayaBaseWhole で棟の全長へ(門の口は札の passage で空ける)。全部埋まる駒は PlaceCastleRun が置かない(N18・N40_1 は殆ど置かれない ── 埋まっていれば見えないので可)。
6. 新しい測り `EdoBuild.SoilOverFacesReport`(EdoBuildFaceSoil.cs・真上から 0.1 格子・2 秒): 見え面の土は「面に沿う両脇 0.3 の地表のどちらより 0.05 高い」(根入れ・坂を数えない)・
   _Tooshi は除く。溝の中の土は床(法線 y ≥0.9・天端 −0.08 より下)の上の地表。

**How to apply:** 溝・駒の下の地面を下面で読む器は「裏の面の無い駒」で抜ける ── 抜けたら上の面で読む。地面の歯は天端の縁の節点を先に疑う。欄の書式が二つある back は二つとも読む。
関連 [[mizo-piece-depth-includes-rim-and-skin-covers]] [[return-lost-when-sashizu-text-format-changes]] [[r146-facestraight-hull-span]]
