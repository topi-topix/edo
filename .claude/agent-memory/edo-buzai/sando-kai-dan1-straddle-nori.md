---
name: sando-kai-dan1-straddle-nori
description: 跨ぐ端(B/F)の段石に法を持たせた綴り d±B±N± と、Unity を触らずに据えた姿を prefab の YAML から起こして測る道(2026-09-26)
metadata:
  type: project
---
参道の階の段 1 は野面の隅(1:0.3)と袖に跨ぐ端 `d+0.222B+0.024N+0.300` で焼いた(39650e31)。ビルダーの EnvelopeCut の跨ぎ枝はまだ za を測らず ⚠ で止まる。
**Why:** 部材だけ焼いても CutStairEndsToBatter が跨ぎ(strad)で continue する限り差し替わらない。
**How to apply:** Unity を触れないときは prefab の PrefabInstance の m_Modifications から世界行列を起こし、FBX を Blender で読んで numpy で光線を打つ(scratchpad k1/dump.py の型)。段石は石の割りの内面があるので端は最初でなく**最も遠い**当たりで測る。

**野面を焼き直した巡は、跨ぐ端の d・za を据えた今の駒で測り直してから焼く。** 背を尻すぼみにした(cdbff6ec)だけで段 1 の za が +0.024→−0.031 と 5cm 動いた(d も 1〜2cm)。野面の駒の焼き直しを自分が出したら、その巡の報告に「跨ぐ端と包絡の一覧は測り直しが要る」と一行添える。za は負もとる(綴り B-0.031・生成器と C# とも通る)。
