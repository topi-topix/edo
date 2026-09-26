---
name: regression-claim-diff-prefab-first
description: 「この巡の建て直しで悪化した」と言われたら、まず git の prefab で駒の位置・回り・部材の GUID を比べる。動いていなければ測りの差
metadata:
  type: project
---

2026-09-26 EDO-0437 仕舞いの検査で「郭の階の袖×隅 0.41→0.82・女坂の袖×SW の隅・腰石垣の裏向き 0/213→1/212 はこの巡の副作用」と来た。
prefab の YAML(PrefabInstance の m_Modifications の m_Name / m_LocalPosition / m_LocalRotation と m_SourcePrefab の guid)を
5aef6990・d27efa4a・68681826 で比べると 3 件とも**一つも動いていない**。悪化に見えたのは検査の母集団の差(前は 000f だけ・今は 001f〜003f も)
と、皮(EdgeSkin)の張り替えで描かれた地表が変わり見え面の票が入れ替わったこと。

- 郭の階の南の袖 TW_GushoKai_S は 4 駒とも**全身が** `TW_Gusho_EK_x_SE_kado`(Ishigaki_Kado_90_H0400)の EK の腕の中。
  隅の局所 +X(EK の腕)は 2.00 あるが、EK の走りは 1.36(E の面の線まで)。袖の坂下の端 = 隅の局所 x −0.041。
  ⇒ 腕を −0.04 で切った隅が要る(焼いた A159x200 は「入り 0.41」を腕の長さと取り違えた値で効かない)。
- 腰石垣の `TW_Koshi_W_009f` は出隅の端の駒の窓の測り点がとなり(SW)の体の上の皮に落ちて裏返る → `EdoBuild.LowSideAwayFromWalls`。

**Why:** 副作用と決めつけて直す関数を探すと、動いていない所の差分を追って時間を失う。
**How to apply:** 悪化の申告は、まず prefab を git で比べる(scratchpad の pf.py の型: PrefabInstance ブロックを m_Name で引く)。
関連 [[measure-dont-nudge]] [[short-return-tie-and-sode-extent]]
