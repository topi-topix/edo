---
name: assets-claim-blocks-fbx-probe
description: 他セッションが assets を握っている間は blender を含む Bash が読むだけでも門番に止まる。FBX の実測は純 python の binary 読みで足りる
metadata:
  type: project
---

2026-09-14 松江松平の稲荷(朱鳥居の分離)で踏んだ。山王の部材方が `assets` を握っていて、読むだけの `blender --background` による probe も、コマンド位置に `blender` がある grep も `check-bash` に止められた。
⭕ FBX binary 7400 を zlib で解く純 python(scratchpad の `fbxprobe.py`・約70行)で Model/Geometry/Material の数と頂点の bbox が取れた(単位は cm・Y-up・+Z front)。一体か分かれているかの判定と、在庫 FBX が生成器のコードと一致するかの確認はこれで済む。⭕ 生成器の `Mesh` 系は bpy・mathutils・vklib・build_goten_roof を `sys.modules` に差す stub で頂点を数えられる(生成器が自分のディレクトリを sys.path の先頭に入れるので、stub はパスでは効かない)。

**Why:** 書き出しの排他は `assets` 資源の単位で効き、読むだけの呼び出しも区別しない。
**How to apply:** 握られていたら待つ間に「コードで数える → 在庫 FBX と頂点数・bbox を突き合わせる」を先に済ませ、Blender は書き出しとレンダだけに使う。関連 [[sanno-faces-unbaked-endfrom]]
