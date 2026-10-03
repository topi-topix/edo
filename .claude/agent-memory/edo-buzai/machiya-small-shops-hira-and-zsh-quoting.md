---
name: machiya-small-shops-hira-and-zsh-quoting
description: 門前の小店(2・3間の厨子二階/平屋)を焼いたときの罠 — zsh は "$a" を割らず既定の5間を焼き直す・平屋は OVER_Z が 0.096・妻壁の天端は瓦の谷から覗く(2026-10-01 EDO-0503)
metadata:
  type: project
---
- ⛔ zsh で `for a in "--ken 2 ..."; blender ... -- $a` は引数が1語のまま渡り、**既定の Typ_Omotedana_5ken を上書き**した(git checkout で戻した)。引数は関数 `run(){ ... -- "$@"; }` で渡す。
- 平屋(前後とも急勾配の軒)は袖瓦の端が軒先線より 0.096 出る ⇒ `OVER_Z_HIRA`。厨子二階の 0.0805 は前 0.065/後 0.096 の平均。
- 狭い駒(2間)は瓦格子の片側のけらばに平瓦の谷が来て妻壁の漆喰が白く覗く ⇒ 妻壁の天端を `GABLE_SINK` 0.08 下げた。
- `PartSpecs` が他窓の claim 中は生成器の札も書けない(門番は blender の書き込みを止めない)⇒ `SPEC_DIR` 環境変数で scratchpad へ。
関連 [[machiya-omotedana-bbox-and-kit-noren]] [[small-roof-tile-scale-and-panel-gaps]]
