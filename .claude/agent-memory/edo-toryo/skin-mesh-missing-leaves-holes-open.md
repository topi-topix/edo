---
name: skin-mesh-missing-leaves-holes-open
description: 皮の段プレハブが指すメッシュ資産が消えていると S1 の ClearEdgeSkins が穴を塞がず、4b が「既に穴で触らず」で空の皮を焼く
metadata:
  type: project
---
症状(2026-10-06 土井 r17): S1 が「縁の皮を外して塞いだ升 0」(前の巡は 1017)。続く 4b が「穴 0 升・既に穴で触らず 1017・皮 頂点 0」で空の皮を焼いた。
原因: `Parts/Edo_Yashiki_DoiOsumi__EdgeSkin.prefab` の m_Mesh が指す資産(前の巡の c1b77a0e)が消えていた ── 前の巡の後で 4b がもう一度走り、新しい皮(3d917cb2)を焼いて旧い資産を消したが書き戻されず、コミットは新しいメッシュだけ入って段プレハブは旧い guid のまま。ClearEdgeSkins は sharedMesh が null だと穴を塞がずに子を消すだけ。
対処: 孤児のメッシュ(頂点数が前の巡の 4b の報告と一致する物)を読み、その三角形の升のうち穴の物だけ SetHoles で塞ぐ(配列は [y,x] で組み直す)→ 4b を流し直す。S1 の「塞いだ升」が前の巡の「穴」の数と食い違ったら 4b の前に止まって調べる。
関連: [[unity-kill-leaves-holes-without-skin]] [[terrain-detail-array-dims-lie]]

再発(2026-10-07 岡部 第49巡): 3b の途中で Unity がメモリ不足で落ち、作業場を開き直すと EdgeSkin の mesh が消えた資産 → 3b が「既に穴で触らず 1298・皮 頂点 0」。
最後にコミットした皮(`git checkout -- Assets/Edo/Meshes/Gen/EdgeSkin_<邸>_<id>.asset*`)を EdgeSkin の子へ差すと、今の穴 1298 升が全部その皮の升の中に入っていた
⇒ 3b を流し直して塞いだ升 1298・頂点 103316(元と一致)で戻った。⭐ 差す前に「今の穴 ⊆ その皮の升」を数えて確かめる(GetHoles は平らに読む)。
