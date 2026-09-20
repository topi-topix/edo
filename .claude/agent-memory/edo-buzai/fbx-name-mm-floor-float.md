---
name: fbx-name-mm-floor-float
description: 出を mm で floor して FBX 名に埋めると浮動小数で 1 mm 落ちる(0.300−0.002 → 297)。既存名との一致を崩すので丸め方を黙って変えない
metadata:
  type: feedback
---

FBX 名の mm は `floor((面 − 余白)×1000)` で、0.29799… が 297 になる(楼門の坂下の門 k297 はこれで出来た名)。
**Why:** 2026-09-14 に round(…,6) の保護を足したら、図が動いていない ±X が 297→298 に変わり、既存 FBX と名がずれた。
**How to apply:** 名を寸法で持つ部材では丸め方を変えない。直すなら既存 FBX・EdoAssets の登録と一緒に作り直す判断として普請奉行へ上げる。
