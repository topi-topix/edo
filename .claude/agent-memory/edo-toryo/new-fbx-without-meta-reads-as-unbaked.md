---
name: new-fbx-without-meta-reads-as-unbaked
description: 部材方がコミットした FBX に .meta が無いうちは LoadAssetAtPath が null で「焼いていない」と出る。流す前に AssetDatabase.Refresh と remap
metadata:
  type: project
---

症状(2026-09-24 EDO-0430 山王): 部材方が IshidanSode_*_D3.20 と透塀 1928/2117 をコミットした直後に Stage2 を流すと、
`PlaceIshidanSodeByDepth` が「焼いていない丈: 3.20」で女坂の袖 5 駒を退けた。FBX は在るのに .meta が無い(Unity が未 import)。
対処: 部材方の後に流すときは、まず `AssetDatabase.Refresh()` → `ls <FBX>.meta` で import を確かめ → `Edo/山王社/新造部材のマテリアルをremap` → Stage。
⚠ 新しい .meta はプレハブが GUID で指すので、書き戻した後に**プレハブが参照する未追跡の .meta**を拾ってコミットに入れる
(`grep guid` でプレハブと突き合わせる。前の巡の Dan_0.200 などの .meta も未追跡のまま残っていた)。

関連: [[prefab-yaml-has-guids-not-names]] [[sode-groundhi-lift-limit]]
