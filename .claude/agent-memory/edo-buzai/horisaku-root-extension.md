---
name: horisaku-root-extension
description: 柵の根を延ばすときは元の杭の箱を伸ばさず下に根の箱を継ぐ(UV が引き伸ばされて見え面が変わる)。地上の頂点+UV を読み戻して差0で示す(2026-10-15 HoriSaku_R0.60)
metadata:
  type: project
---
- `build_hori_saku.py --root=0.60`: Mesh.box は UV 矩形を全長に貼るので、杭を −0.60 まで伸ばすと地上の木理が縦に縮む。⭕ −0.12 の下へ根の箱を足す(継ぎ目は地中)。検算は y>−0.12 の (頂点, UV) 集合を元の FBX と比べて差 0。
- 普請方の根の条件は「板の下端から 0.50 以上【硬】・0.60 狙い【柔】」(第139巡)。
- zsh では `$P` に改行区切りの名簿を入れても割れない ⇒ git の pathspec は glob を引用して渡す。
**How to apply:** 根入れ・地中の延長は元の部材の見える頂点を動かさない。関連 [[tategoshi-saku-module-and-hori-saku-axis]] [[machiya-small-shops-hira-and-zsh-quoting]]
