---
name: nagaya-miter-cut-signed-anchor-seal
description: 表長屋の切る留めを入隅(θ<0)・門長屋・両端へ広げた時の罠 ── 延ばしの探索は両端で窓が Q に掛かる・門は割付を据え置く・座の違う相手は断面の板(2026-10-16 岡部 EDO-0502)
metadata:
  type: project
---
- `--miter-cut` の延ばしを長さで解き直す探索は**両端を留めると窓が Q に掛かる**(17.63 で −0.30)⇒ 両端・門長屋は `--layout <長さ> <L|R|C>` で割付を据え置き、留める端に 1.5間の窓割りを差し足して切る(cut_miter_anchor)。Q の窓は 1.381±0.69 で外れる。
- 岡部の外周は**ほぼ全部の角で座が違う**(V40 0.5・V18 0.9・V41 0.3)⇒ `--seal` で切り口に断面の外形の板(下は躯体の内だけ土台の底まで・軒の出は軒裏)。⛔ 躯体の表を「低い点の最大」で取ると浮き彫りの点で軒下に鰭が立つ ── 表は壁の外面 +0.035 固定。
- 光線の検めで面の上ちょうど(off=0)を通る線は継ぎ目の掠りで素通りに数える(偽陽性)。マゼンタは world を Light Path の camera ray だけにしないと全体が染まり穴と区別できない。

**How to apply:** 座か控えの違う相手と留めるなら --seal。門・番所・--wide のある駒は --layout。関連 [[nagaya-miter-cut-convex-corner]] [[double-kado-and-nagaya-miter]] [[magenta-background-finds-holes]]
