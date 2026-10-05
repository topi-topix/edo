---
name: tree-buried-in-wall-blocks-skin-hole
description: 土留めの中に埋まった地形の木が皮の穴を2升ぶん止め、2m 格子が駒の下の節点を見え面の前へ描いて土の尾根と背の隙を作っていた ── EdoBuild.RetireTreesInParts で先に退ける
metadata:
  type: project
---

2026-10-05 EDO-0502 第27巡(岡部 西の返し TW_Minami_Koshi#ret0)。

症状: 見え面の 0.4m 前の描かれた地表 20.10(溝の設計 19.2)・背の角の隙 0.35。前の巡は「盛り残り」と見て S1 から流したが消えなかった。
原因: 低木 Tree_Teiboku_H24_02(地形の木・出所の Stage は不明 ── 前の類型か旧い巡の残り)の幹の足が返しの駒の外形の中。
3b は地形の木を plantPoints として ±0.40m の升を守る ⇒ 見え面の前の升と駒の升の 2 升に穴が開かず、地形の 2m 格子が描いていた。
対処: `EdoBuild.RetireTreesInParts(poly, parts, log)` を 3b の plant 集めの前で呼ぶ。1 本退けて 尾根 0・元からの隙 6→0。

**How to apply:** 皮の縁に説明のつかない土の尾根・隙が出たら、先に `td.GetHoles` で穴の升を刷り、穴でない升に地形の木が立っていないか見る。
⚠ GetHoles は正方の塊で読む(寸法の名札が逆)。木の退けは TerrainData の中 ── ModernTerrain.asset を退避してから。
関連: [[backbench-residue-cleared-by-stage1]] [[terrain-holes-and-skin-traps]] [[terrain-detail-array-dims-lie]]
