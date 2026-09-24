---
name: own-tree-fbx-invalid-as-terrain-tree
description: 自作の木の FBX(Tree_Matsu/Keyaki/Jouryoku ほか 33 原型)は地形の木として無効で一本も描かれない — 根に MeshRenderer も LODGroup も無い
metadata:
  type: project
---

症状: 山王の社叢の地形の木 1030 本がレンダに写らず、見えていたのは GameObject の低木(3〜5m の丸い株)と名木 20 本だけだった(2026-09-23 EDO-0401)。
原因: Assets/Edo/Models/Trees/*.fbx は根が Transform だけで子に LOD_0/1/2 の MeshRenderer が3本。Unity の地形の木は根の MeshRenderer か LODGroup しか受け付けず、`TreePrototype.Validate(out msg)`(internal・reflection で呼べる)が "couldn't be instanced because the prefab contains no valid mesh renderer" を返す。コンソールには何も出ない。縮尺・根元の高さ・treeDistance は全部正しかった。
対処: 地形の木に使う前に reflection で Validate を叩く。同じ FBX を GameObject で置くと LODGroup が無いので LOD_0/1/2 が3枚重ねで描かれる(名木・低木も同じ)。直すのは部材方(LODGroup を持つ原型にする/子を `*_LOD0` 命名にして取り込みで LODGroup を生やす)。
