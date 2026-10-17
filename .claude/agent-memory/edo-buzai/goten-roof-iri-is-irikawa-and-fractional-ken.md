---
name: goten-roof-iri-is-irikawa-and-fractional-ken
description: 御殿の munes[].iri は入母屋の印でなく入側の間数・岡部の御殿の屋根は帯割りでなく素の Irimoya_<w>x<d>ken・端数の間数は float 版(2026-10-04)
metadata:
  type: project
---

岡部の御殿5棟は `roofs[].asset = Own.RoofIrimoya_(w,d)` → `build_goten_roof.py -- <W m> <D m> Goten_Roof_Irimoya_<w>x<d>ken`(帯割り Banded ではない)。`munes[].iri` は **入側の間数**(EdoOkabeYashikiBuilder.PlaceMunes)で、依頼文が「入母屋」と読んでいても値1なら意味は同じに落ちる。
**Why:** 土井の7棟(EDO-0533)で依頼が iri=入母屋と書いていた。12×8.5 の長局は int 版で引けないので `Goten.RoofIrimoya_(float,float)`(KenTag の綴り)を足した。
**How to apply:** 既に焼けている寸法(6x5/8x6/11x9 ほか)は焼き直さず流用。zsh で "14 10" を for で回すと割れない → 関数に位置引数で渡す([[machiya-small-shops-hira-and-zsh-quoting]])。
