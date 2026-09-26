---
name: recalc-normals-inverts-folded-stone
description: bmesh.ops.recalc_face_normals は輪の折れた塊を丸ごと内向きに揃えることがある — Unity の裏面カリングで天端に四角い抜け。符号付き体積で外向きを保証し、真上からの光線で「裏に当たる点」を数える
metadata:
  type: feedback
---

2026-09-26 EDO-0437 棟梁のレンダで山王の野面の天端に四角い抜けが 2 か所(H0900_d / H0600_b)。原因は天端の列の表の石が**丸ごと内向き**に焼けていたこと(尻すぼみ+割肌で輪が折れた塊を recalc が裏返した)。Blender の EEVEE は両面を描くので検証レンダでは見えない。調べると 182 駒中 64 駒・77 石が同じ欠陥だった。

- ⭕ `build_sanno_nozura._orient_out(bm)`: recalc の後に符号付き体積 < 0 なら全面 reverse。塊を作る関数には必ず通す。
- ⭕ 検査 `-- holes`: 真上から 1cm 格子で光線、最初の当たりが裏(nz < −0.05)か、周り 4 方向を天端の帯に囲まれて 0.25 より深い点を塊にし、0.05 角が丸ごと入る塊だけ穴と数える(目地は数えない)。
- ⚠ 開いた島(継ぎ目で切った端の石)の符号付き体積は原点次第で負に出る — 判定は光線で。検証レンダは `use_backface_culling=True` にすると Unity と同じに見える。

**Why:** crest・check・kado-check は全部 ⭕ のまま通っていた。裏返った面は「高さ」の検査には正しい高さで写る。
**How to apply:** 石・塊を bmesh で閉じて作る生成器では、面の向きを体積で保証し、真上からの裏当たりを数える。関連 [[mesh-box-inward-normals-and-ray-checks]] [[magenta-background-finds-holes]]
