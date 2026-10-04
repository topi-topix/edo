---
name: matsudaira-banded-gable-noki-and-hirairi-notch-log
description: 松江松平の帯割り屋根3点は妻側の軒0で生成器が止める・平入りの照会文は --notch を落とす・内長屋は梁間2.75間(2026-10-04)
metadata:
  type: project
---

EDO-0554 の照会のうち Genkan(4,4x10 v n0110)/Omotegoten_0(3,4,5x36 u n0011)/Omotegoten_1(4,4x6 v n0101)は **妻側(along の辺: u なら u0/u1・v なら v0/v1)の軒を 0** にしていて `make_banded` の止めに当たる(破風が宙に浮く)。焼かずに返した ── 屋根の形(両下・招き・棟の向き)を指図で決め直す話。
**Why:** ビルダーの noki は外形の接触から機械的に出るので、妻で隣と接する棟にも 0 が立つ。
**How to apply:** banded の照会は焼く前に `_map_sides` で妻の辺を引き、0 なら焼かずに差し戻す。`EdoMatsudairaDewaBuilder` の平入りの照会文は `--notch` を書かない(名の `_k..` から補う)。内長屋 Uchi_* の梁間は 2.75間(Obi_Nagaya_<L>x2.75ken)。build_obi_nagaya の --render は名に寸法が入らず上書きされる。
