---
name: neribei-no-koshi-nk
description: 練塀の腰なしの駒 *_NK を全 607 本焼いた時の作りと罠(下見板は2段を継ぐ・名の一覧から引数を復元・素の build は Assets へ書く)(2026-10-13 EDO-0502)
metadata:
  type: project
---
2026-10-13 施主「塀の底の腰の石垣と台の石垣の二重が違和感」で build_neribei.py に `--no-koshi` を足し、名の末尾 `_NK` の別の駒として並べた(腰ありは残す・台の上=腰なし/地面に直=腰あり)。

- 下見板は縦に伸ばさず、素の 2 段(0.4228)を切り出して下へ継ぎ z=0 で切る。底は板 "soko"(tome の切りで消えないよう shin と別の群)。札の足元は ±0.206(腰ありは ±0.337)。
- 全種の引数は Assets/Edo/Models/Neribei の名から正規表現で復元できる(腕 A85x26 も cm で焼けば屋根の頂点が旧と 1mm で一致した)。旧と新を FBX で読み直して屋根の頂点の多重集合を比べると回帰が一発で示せる。
- ⚠ 確かめのつもりで素の `--choku` を BUZAI_OUT 無しで回すと Assets の FBX を上書きする。並行作業中は必ず BUZAI_OUT を付ける(やったら git checkout で戻す)。zsh の `$a` は割れない → `${=a}`。

**How to apply:** 腰なしを焼き足すときは同じ一覧に `--no-koshi`。[[neribei-saka-shear-and-tome]] [[machiya-small-shops-hira-and-zsh-quoting]]
