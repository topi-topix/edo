---
name: tomebashira-goten-column-and-dobei-kasa
description: 練塀の留め柱(6寸角)は在庫の Goten_Column で足りる・練塀の笠の下は座 +2.274(2026-10-12 岡部 EDO-0502)
metadata:
  type: project
---
- 6寸角 0.18 の柱は在庫 `Goten.Column`(0.182 角 × 2.727・材 wood)。新造しない。Blender で読むと角が原点(中心ピボットではない)⇒ 実メッシュで測って据える。
- 練塀の駒 s_hei_center は座 −0.10 が下端・壁の天端(笠の下)は生 1.306 × ES ⇒ **座 +2.274**。柱の天端をそこへ置くと下端は座 −0.453。
- 倍率の基壇の隅は `build_kado.py --s <s>` を回して .meta を写し guid だけ替える(S042 = 実寸 1.68)。
**How to apply:** 練塀の端の留め・柱の丈合わせ。関連 [[kidan-scaled-kado-and-fuchi-mizo]] [[dobei-kado-batch-meta-clone]]
