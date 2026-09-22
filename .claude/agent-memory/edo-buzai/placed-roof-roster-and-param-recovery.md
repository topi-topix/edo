---
name: placed-roof-roster-and-param-recovery
description: 据えてある御殿屋根の名簿は .meta の GUID をプレハブへ grep して採る。帯割り・平入りの生成パラメタは指図 json から機械で復元でき、ファイル名から逆算しない
metadata:
  type: project
---

**「据えてある」御殿屋根の名簿は、FBX の `.meta` の `guid:` を
`Assets/Edo/Prefabs/**/*.prefab` へ grep して採る。**`Roofs/` には 84 本あるが
プレハブから参照されているのは **52 本**だけで、残りは旧寸法・試作(2026-09-22 実測)。
⛔ ディレクトリの一覧や mtime で対象を決めない。⚠ 邸は段へ割ってあるので
`Prefabs/Scene/Parts/**` も含めて走査する(帯割り・平入りは `<邸>__Buildings.prefab` に居た)。

**⭕ 生成パラメタは「ファイル名から逆算」ではなく「指図 json から機械で復元」する。**
名前は幾何の**識別子**であって仕様ではない — `eave`(軒桁高)・`noki_de`・`tsuma_end`・
`hon/his/hken` は名前に入らないので、名前だけでは焼き直せない。

| 型 | 復元の出どころ |
|---|---|
| Irimoya | 名前の `<W>x<D>ken` だけで足りる(`make_irimoya(W*KEN, D*KEN, name)`) |
| Banded(松江松平 7本) | `matsudaira_dewa_sashizu.json` の `munes[].roof`。軒を落とす辺は `build_matsudaira_dewa_roofs._touching()` が外形から解く ⇒ `_n` の綴りも自動で一致 |
| Banded(土井 5本) | 指図に `bands`/`spanKen` が無いので**名前から**。ただし `const.gotenEave` 3.4 / `nokiDe` 0.9 / `tsumaEnd` 0.3 が**生成器の既定と同値**だと確かめてから |
| Hirairi(5本) | `build_matsudaira_dewa_roofs.plan_hirairi()` がそのまま出す。`_e2744` = `nagayaGataEave` 3.364 − `gotenFloor` 0.62、`_e2410` = `umayaEave` 3.03 − 0.62 |
| Kirizuma / RokaGeya | `-- kirizuma <間数>` / `build_matsudaira_dewa_roofs.py -- --geya`(後者は指図の `links[].kind=="渡廊下"` から 2/4/6ken を出す)。どちらも既定のまま |
| Noboriro(2本) | **指図にも C# にも寸法が無い**。斜長は既存 FBX の X から `W = hi.x − 0.30(end)− 0.069(棟の出)`、幅は Y が Kirizuma と同一 ⇒ `KEN`。W1 10.82 / W2 14.42 |

⛔⛔ **コミット文の散文を仕様として読まない。** `aa7edbae` は登廊を「いずれも幅4.4m」と書くが、
焼いてある FBX の梁間は **Kirizuma と 1mm も違わない 3.135m(= KEN + 軒 0.60×2 + 軒瓦 0.117)**。
4.4m は**柱の芯々**(「段の芯から左右 2.00m」)の値で、屋根の幅ではなかった。
⭕ 数値は**焼いてある物を測って**復元し、散文は裏取りにしか使わない
(2026-09-22 EDO-0394 で実測。値は `EdoAssets.Goten.RoofNoboriro` のコメントへ書き戻した)。

⇒ **焼き直しの駆動は既存の生成スクリプトの `plan()` 系を import して回すのが最短**
(scratchpad に薄い runner を書いて `--only` で絞る)。
⛔ `build_goten_roof.py -- rebuild` は使わない(`docs/session-coordination.md:178`)。

**⭕ 巻きだけが変わったことの示し方(2026-09-22 EDO-0393・31本の実測)。**
頂点数・面数は **31本すべて完全一致**、bbox の差は **0.01mm 未満**、最大移動 **0.235mm**、
材質スロット名も一致。面は**位置の巡回を 1mm へ丸めて**突き合わせると
**反転 316〜2231 面 / 不一致 144〜481 面**(不一致は棟が 0.2mm 動いたぶん)。
⇒ 「反転」が出て「頂点数と bbox が動かない」なら、それは巻きだけの直し。
測り方は [[rebake-regression-by-vertex-multiset]]。

**⭕ 同じ不良の Kirizuma / Noboriro / RokaGeya 15本も焼き直した**(2026-09-22 EDO-0394)。
`ridge()` を呼ぶが `oni()` は呼ばない型。頂点数・面数・材質スロット名は 15本すべて完全一致、
bbox の差 **0.0002mm 以下**、最大移動 **0.200mm**(`RIDGE_W` の丸めぶん)、
反転は **切妻 30〜210 面 / 登廊 130・170 面 / 下屋 40〜120 面**。
⛔ `.meta` は 1本も変わらないので **remap は要らない**(材質スロット名が同じで、
`.meta` の `externalObjects` が `roof` / `roof ornaments` / `wood` を GUID で留めている)。
`Amaosae` は `GR.ridge` を使わないので無関係。

関連 [[ridge-module-mirrored-and-koguchi-arc]] [[magenta-background-finds-holes]]
[[baked-roster-is-json-not-disk]]
