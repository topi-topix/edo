---
name: one-mesh-part-split-by-submesh
description: 一体で焼いた駒(隅櫓・門・祠)は屋根をメッシュの名で落とせない。材(サブメッシュ)の名で分け、屋根の最下点より下を躯体とする
metadata:
  type: project
---

**症状**: 隅櫓 Y_NE の「躯体が区画線を越える量」を測ろうとしたら、`EdoBuild.Body`/`BodyAt(withRoof:false)` が
**屋根まで込み**で返した。`IsRoofName` は `yane/noki/taruki/mune/keta` を見るが、この駒は
MeshFilter が**1個**で名前が `Matsudaira_SumiYagura` だから何も落ちない。

**実際の作り**: 1メッシュ・**6サブメッシュ**で、材の名が役を持っていた —
`Fence_B_01`(板壁)/ `Wall Exterior Defence`(漆喰壁)/ `roof` / `roof ornaments` /
`wall C`(二層目の妻壁)/ `wood`(二層目の柱)。**同じ駒の中で越え量が 0.347〜1.469m とばらける**ので、
どれを「躯体」と呼ぶかで答えが倍半分違う(松江松平 2026-09-21 の裁定はここで割れた)。

**対処**: `EdoBuild.BodyBelowRoofAt(path,pos,yaw)`(2026-09-21 新設)—
材の名(`IsRoofLabel` = `IsRoofName` + roof/屋根)で屋根のサブメッシュを見分け、
**その最下点より下に居る頂点だけ**を返す = 一層目の躯体。⛔ `座+2.0m` のような帯を数で決め打ちしない
(屋根の高さは部材が決める)。⛔ `IsRoofName` 自体は広げない — `Body()` が使っていて他邸の実測が黙って動く。

**ついで**: 隅の駒の入れ量は `(半幅+犬走り)÷sin(内角の半分)` を**下限**にして、実メッシュが線を越えるぶんだけ
内へ足す(`YaguraSeat`)。二等分線に沿って 1m 入れると辺 e の越えは `-dot(bis, outward_e)` だけ減る
(松江松平の隅では 0.7988)。⚠ 二等分線は**走り方向にも効く**(辺13 へ -0.6016/m)ので、
隣の長屋へ近づく — 寄せたら取り合いを測り直すこと。
