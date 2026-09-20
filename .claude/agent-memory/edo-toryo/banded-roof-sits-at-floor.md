---
name: banded-roof-sits-at-floor
description: 帯割り屋根(Goten_Roof_Banded_*)は FBX が軒高を焼き込んでいる — 床へ据える。軒下端を軒高へ寄せ直すと 0.71m 浮く
metadata:
  type: project
---

**症状**: 帯割りの御殿 8 棟だけ屋根が全周 0.39m 浮く(屋根底 30.74 / 柱天端 30.35)。
入母屋・切妻は正しく噛んでいるので「部材が悪い」に見える。

**原因**: `EdoGotenKit.Mune(roofEaveLocalY: …)` は**実メッシュの最下端**を
`(floor − NUREEN_DROP) + 軒高` へ寄せる。ところが `build_goten_roof.py:make_banded` は
**z=0 = 床**で、引数 `eave` = 指図 `const.gotenEave`(**床上の身舎の軒桁**の高さ)を
**すでに焼き込んでいる**。「軒下端(濡縁上)」と読んで寄せ直すと
**0.712m 浮く** = 入側1間+軒の出の下がり 0.992 − 濡縁 datum の差 0.28。

**対処**: 帯割り(`roofAtFloor`)には `roofEaveLocalY` を渡さない(NaN)。
土井の帯割りは最初からそう据えている。検算は指図の従属値
`min(辺)[ gotenEave − (入側[間]×ken + 軒の出) × 瓦勾配 ]` と実測の差で見る
(実測は**軒先瓦の垂れ 0.127m** ぶん下に出る — 垂れは部材の持ち物で指図は持たない)。

⚠ **知っておくべき副作用**: 帯割りを正しく床へ据えると、御殿の軒(入側の外の柱通りで
floor+2.408)が**渡廊下の大棟**(kit 定数 `ROKA_EAVE` 1.55 + 棟 0.953 = floor+2.503)より
低くなり、廊下の屋根が御殿の軒へ **最大 0.713m 食い込む**(実測)。
kit の見張り `RokaRidgeTop > MUNE_EAVE` は**入母屋の軒高 2.577 を基準にしている**ので鳴らない。
⇒ 渡廊下の軒高・棟高は**どの邸の指図も持っていない**(kit の定数のまま)。裁定案件。

関連: [[checkscene-center-vs-seat]]
