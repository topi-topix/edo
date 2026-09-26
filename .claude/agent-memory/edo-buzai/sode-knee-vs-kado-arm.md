---
name: sode-knee-vs-kado-arm
description: 袖が隅の法の足に当たるのは腕の長さでなく袖の膝 ── KadoArmNeeds の「要る腕 0」を鵜呑みにすると壁に 0.8m の口が開く
metadata:
  type: project
---

2026-09-26 EDO-0437(山王 前庭の北東 TW_Zentei_N_kado2 × 参道の階の東の袖 001f・0.035〜0.040)。

- 棟梁のビルダー(EdoBuild.KadoArmNeeds)は中と読んだ頂点を**留めの二等分線で腕へ振り分け、走りの最小**を要る腕とする。袖が片腕の**見え面の前**に
  立つと、袖の端が P の走り 0 に在るだけで「要る腕 0.00」と出る。実際は腕2 の法の足(床から 0.2 下まで前へ出る)が袖の**膝(−0.60)より下の
  鉛直の背**を貫いていた。腕を 0 にすると N_026f との間に 0.8m の口が開き、埋めた直線の駒が同じ所で当たるだけ。
- 直しは袖の側: `IshidanSodeNozuraNori` の背の法を**袖の底まで通す**(NNORI_KNEE = None)。名は同じ・膝より上は不変。8方向の光線で 18/113 点 → 0/0。
- Unity を触らずに確かめる道: 棟の scratchpad の k1/dump.py(prefab の YAML から世界行列)+ tri.py(FBX → 世界の三角形)+ numpy の 8 方向の光線。

**How to apply:** 「腕を詰めた隅」を頼まれたら、まず相手の頂点が隅の**どの面の前**に在るかを局所座標で見る。見え面の前なら腕でなく相手(袖)の背を相手の法で切る。
関連 [[nori-cut-step-and-sode]] [[castle-wall-kiri-and-short-arm]] [[sando-kai-dan1-straddle-nori]]
