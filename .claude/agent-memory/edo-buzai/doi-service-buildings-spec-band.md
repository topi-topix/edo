---
name: doi-service-buildings-spec-band
description: 土井の附属屋10点(厩5x11・蔵4x4.5置屋根・供待・御駕籠蔵・惣後架・稲荷・家中11〜14)を焼いた時の罠 — 札の帯の刻みと床、tomomachi の float、置屋根の水切り、流造の妻の隙(2026-10-04)
metadata:
  type: project
---
- 札(building)の front/back は帯 0.30+0.25n の**刻みの断面だけ**で測られる。供待の縁の床板(0.62〜0.72)は 0.55/0.80 の間に落ちて入らず、正面は礎石(芯+0.26)になる。足元は基壇 ±0.13(frame/obi)/ ±0.22(dozo)。下見板の長屋は壁の線+0.03。`_spec` の前検めで設計と実測の差を刷る。
- `OF.tomomachi` の vKen は `range(1, vKen)` に入るので**整数で渡す**(端数の間は uKen=梁間 側へ)。
- `F.dozo(okiyane>0)` は `mizukiri_tooshi=False` を一緒に渡す — 通すと観音扉を水切りの白帯が横切る。
- 前後の勾配が違う流造は妻を三角で塞ぐと隙が残る。身舎の天端→裏板の線の五角形で塞ぎ、背面の壁も裏板まで立ち上げる。
- DoiKura は float 引数に変えた(名 "4.5")が、EdoDoiBuilder は端数の間の蔵を Wait で退ける(棟梁の側の直し)。
