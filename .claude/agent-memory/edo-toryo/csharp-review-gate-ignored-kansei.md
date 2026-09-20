---
name: csharp-review-gate-ignored-kansei
description: C# の検図関門が kansei の phase を見ておらず、python の review_gate が ⭕ でも Stage が止まっていた(2026-09-20 に直した)
metadata:
  type: project
---

`EdoSashizuExport.ReviewGate` が指図の `reviews` しか読まず、`<邸>_kansei.json` の
`phase`(built/done)を見ていなかった。⇒ `python3 Tools/Sashizu/review_gate.py <邸>` が
**⭕「実装後(phase=built)— 検図関門は効かない」**と言うのに、Stage を呼ぶと
**⛔ 検図関門が赤**で止まる、という食い違いが出る(松江松平 2026-09-20)。

**Why:** 2026-09-19 施主裁定2=A で関門が `kansei_gate.py` へ移ったとき、python 側だけ直して
C# 側が取り残された。⛔ 散文の規則は両方の実装に写さないと片方が古いまま残る。

**How to apply:** 直して commit 済み(ReviewGate の冒頭で kansei.json を読み、built/done なら null)。
⚠ **止まったら「指図が赤」と鵜呑みにせず、まず python の関門と突き合わせる** — 二つが反対のことを
言っていたら、実装(C#)側が古い可能性を先に疑う。⛔ `--record` で赤を白く塗って回避しない。
