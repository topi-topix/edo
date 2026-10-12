---
name: kidan-saka-shear-castle-wall
description: 台の石垣の坂なりは素の Castle Wall を縦に剪断(局所 Y += g·Z)・天端だけ反らせると重ねで面が割れる・札の共通の欄は Measure の読みに合わせる(2026-10-13 EDO-0502)
metadata:
  type: project
---
2026-10-13 岡部 const.heiLine.kidanCrest 用に build_kidan_saka.py(Ishigaki_Choku_H0400_G<U|D>… 58 本・坂の隅 Ishigaki_Kado_78_H0400_S075_G…x… 4 本)。

- Castle Wall は 38 頂点の箱に石の絵を貼っただけ ⇒ 剪断で石の形は崩れない。根石を水平に残し天端だけ反らす案は 0.2 の重ねで面が 0.25·g·1.8 食い違う(12% で 5.6cm)ので不採用。
- 局所は素の Castle Wall のまま(走り Z・見え面 −X)⇒ EdoPartSpec.Verify は Z を「面」と読む。札の faceOut/faceIn/copingOverhang は Measure の読みを式で入れ、据えの値は crestY/rootY に別に書いた。
- build_kado.py の main を `__name__` で守った(import して load/normalize/extend_down を使う)。隅は焼いた素の隅 FBX を読み直して芯の道のりで剪断(腕の先で直線の駒と頂点差 ≤1e-5)。

**How to apply:** 新しい勾配・丈・走りは `--grade/--h/--len` で焼き足す(.meta を写すので remap 不要)。[[neribei-saka-shear-and-tome]] [[kidan-scaled-kado-and-fuchi-mizo]]
