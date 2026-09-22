---
name: honden-body-does-not-drop-roof
description: EdoBuild.Honden で建てた本堂と山門は Body(withRoof:false) が屋根を落とさない(頂点数が屋根込みと同数)— 「壁体で測るか軒で測るか」を分ける実装は黙って無効になる
metadata:
  type: project
---

**症状** 「参道を壁体でなく軒先で測る」直し(`JishaOmoya` の `var fc = pass == 0 ? rc : wc;`)を入れても、
16 区画の刷りが**1 文字も変わらない**(成満寺 3/4・最小 1.21m のまま)。

**原因** `EdoBuild.Body(honden, n, withRoof:false)` の頂点数が `true` と**同数**(坊の本堂で 22913 = 22913)。
`IsRoofName` は MeshFilter の素性の名(`PartName`)で篩うが、`EdoGotenKit.Mune` が組む入母屋の
メッシュ名に yane/noki/taruki/mune/keta が入っていないので一枚も落ちない。山門(`Mon_sanmon`)も同じ。
→ `rc == wc` なので「軒で測る」と「壁体で測る」は同じ式。分岐は無効。

**対処** 軒と壁体を分けたいなら、まず駒の側で屋根のメッシュに `_yane` を付ける
(`EdoBuildGoten` に同趣旨の改名がある)。⛔ `IsRoofName` の篩自体は広げない(EDO-0355 の逆を踏む)。
**検め方**: 分岐を入れたら `Body(t,n,true).Count != Body(t,n,false).Count` を一度刷って確かめる。

**Why:** 「直したのに刷りが変わらない」を古いアセンブリのせいだと誤診しかけたため(実際は再コンパイル済み)。
**How to apply:** 屋根/壁体を出し分ける実装を書く・読むときは、その駒で実際に分かれているかを頂点数で先に見る。
