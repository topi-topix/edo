---
name: bake-impl-carried-src
description: bake_impl.py は指紋が食い違うと焼ける欄まで書かずに止まる。欄の焼き手を足したら carriedSrc(据え置きの欄が名乗る元)を残さないと未検査が黙って合格に化ける
metadata:
  type: project
---

**症状**: 指図を直したのに `python3 Tools/Sashizu/bake_impl.py sanno --write` が
「算出物が**いまの指図から焼かれていない**」で止まり、**焼ける欄(`corners` など)まで書かない**。
C# 側の `VerifyImplFingerprint()` も同じ指紋を見ているので、算出物を焼き直せないと Stage が一つも流れない。

**根**: この道具が焼ける欄は一部だけで、残り(`graded` / `grid` / `runs` / `terraces` …)は
邸ごとの生成器(afb529c2 で削除)と一緒に焼き手が消えている。指紋だけ刷り直すと**据え置きの欄が
古いまま関門が緑**になるので、以前は「書かない」で守っていた。

**対処**(2026-09-22・EDO-0261 ①): 欄の焼き手を足したら**指紋は刷り直してよい。ただし
`baked.carriedSrc`(据え置きの欄が焼かれた当時の指図の指紋)を残す**こと。報告は `src.sha256` と
突き合わせて「据え置きの欄は別の指図から焼かれたまま」と鳴り続ける(規則19: 未検査であって合格ではない)。
⛔ `carriedSrc` を消さない・⛔ 焼き直せた欄の一覧(`baked.columns`)を水増ししない。

**⚠ 欄を足すときの落とし穴**:
・`BAKEABLE` に足すだけでは `parcels.json` に区画が無い邸(山王は `sanno` という区画を持たない)で
  据え置きに落ちる ⇒ 区画が要る欄は `NEEDS_POLY` にだけ入れる。
・`diff_rows` は行の名札を `id` で引く ⇒ `name` しか持たない欄(`gates`)を足すと KeyError。
・**半分だけ焼かない**。門は向き(`yaw`/`passAz`/`yawFrom`/`front`)しか焼けず、芯(`u`/`v`/`world`)は
  `uFrom` の組み立てが要るので今の行から持ち越す ⇒ **指図に無い門・算出物に無い門があれば `gates` ごと
  据え置き**(`Carried` 例外)にして名指しで刷る。
