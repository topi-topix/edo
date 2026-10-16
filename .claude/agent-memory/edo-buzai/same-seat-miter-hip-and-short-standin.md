---
name: same-seat-miter-hip-and-short-standin
description: 角で同じ座の留めは kera なしの --seal で一つの屋根に回る・30°以上は --cut-kera sumi の隅棟・2間の素の版は妻二つで組めない・素の版は _kutai だけで足りる(2026-10-16 岡部 第150巡 EDO-0502)
metadata:
  type: project
---
- 座の同じ二棟の --miter-cut + --seal は板が背中合わせで見えず、屋根は外が稜・内が谷で一続き(光線の穴 0・突き抜け 0)。座の違う継ぎの --cut-kera hi/lo を残すと切り口に熨斗が立つ ⇒ 付けずに焼き直す。30° 以上の出隅だけ `--cut-kera … sumi`(熨斗の帯を切り口の線に跨がせ、切る面で相手の側の半分を落とす・相手も鏡像の半分)。浅い折れ(≤11.5°)は隅棟なしで一棟の折れに見える。
- 2間 3.636 の素の _kutai は妻二つでは端の間の詰めが上限(DLT_MAX)を越えて組めない ⇒ −X を 0.01° で切った代わりの版(`--miter-cut -0.01 0 --seal --name …_3.64_2f_kutai`・妻なし)。KutaiOf は _kutai が在れば素の _2f を要らない(12.47 も _kutai だけ)。
- 12.225 は C# Len2 でも python fmt でも 12.22 ⇒ 棟梁の一覧の 12.23 と食い違う時は両方焼く。zsh で `$B` に入れたコマンドはまた割れなかった ⇒ 必ず bash の .sh。二棟の並べ焼きは scratchpad の pair.py(札の jamb で Q に据える・Unity 平面で回す)。

**How to apply:** 角の座を揃えた後の留めの版は kera なし・大きな出隅は sumi。短い角の棟は素の版の代わりを焼いて名を合わせる。関連 [[cut-kera-step-roof-and-naname-roof-back]] [[miter-both-ends-length-overshoot]] [[nagaya-miter-cut-signed-anchor-seal]] [[machiya-small-shops-hira-and-zsh-quoting]]
