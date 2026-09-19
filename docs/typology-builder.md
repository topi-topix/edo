# 類型ビルダー — 手作りしない区画を、区画の形と類型から建てる(設計)

**2026-09-19 施主裁定1=A の実装設計。** 88 区画を二層に分け、史料で確かな数敷地だけ手作りし、残りは
**区画の形と類型からビルダーが生成する。類型の区画には指図も検分の輪も無い。**
裁定の記録: https://claude.ai/artifact/EouMVDWUjrGCaDuZ4tUHVW ／ 新しい輪の図 §2: https://claude.ai/artifact/NLH516uX8qR8XnSxPE4Rnh

⭐ この文書は**設計**であって実装ではない。実装は宿題(掲示板)で、着手前に §7 の裁定を施主に仰ぐ。
数値は例で、正典になるのは `docs/Sashizu/typology.json`(§3)だけ。

---

## 1. 二層の判定 — どの区画が類型か

| 層 | 何を | 指図 | 検分 | 完成 |
|---|---|---|---|---|
| **手作り** | 史料で確かな数敷地(単位は邸・神社仏閣・水系土木・町)。**どれかは施主が選ぶ** | 意図と制約だけ(規則2) | 実装前に 1 巡 | 完成条件の表 5 項目(`kansei_gate.py`) |
| **類型** | 残りすべて | **書かない** | 類型表を考証方が**一括で 1 巡** | 隙 0・境界侵犯 0・埋没浮き 0 + 一括レンダの施主承認 |

手作りの**候補**(裁定図の列挙。確定は施主): 山王社(`sannosha_prec`)・松江松平(`matsudaira_dewa`)・岡部(`okabe`)・
土井(`doi`)・京極(`sannobuke_kyogoku`)・外堀(工区。区画外)。⛔ 候補であって決定ではない — 施主の一言が
出るまで、新しい敷地を手作り層に入れない(`docs/fushin-bugyo.md` ③)。

`parcels.json` の 88 区画(`category` の内訳・2026-09-19):

| category | 区画数 | 類型の軸(径数の元) | 既存の街区ビルダー(先行例) |
|---|---|---|---|
| `buke` | 37 | 上/中/下屋敷・旗本の別 × **石高帯**(→ 門の格式・外周・主屋の型) | `EdoYashikiBuilder`(三屋敷)/ `EdoSanbezakaBuilder` / `EdoSannoBukeBuilder` / `EdoNishiTameikeBuilder` ほか |
| `machiya` | 27 | 片側町 / 両面町 × **間口(間)** × 裏長屋の有無 × 番屋・稲荷 | `EdoTamachiBuilder.Cho`(表店の並び `pattern`・`nUra`)/ `EdoShinmachiBuilder` / `EdoDaichiBuilder` |
| `jisha` | 15 | 社僧の坊 / 寺 / 社家 × 本堂の間数 × 門の型 | `EdoSannoJuboBuilder` / `EdoTodaBlockBuilder`(澄泉寺・陽泉寺) |
| `kouyuu` | 8 | 御預明地 / 干場 / 火消屋敷 × 地表の仕上げ | `EdoAzukarichiBuilder` |
| `other` | 1 | 松平大和守(9,661 坪。手作りか類型かは施主) | — |

⭐ **既存の街区ビルダーは類型ビルダーの先行例**であって敵ではない。`EdoTamachiBuilder.Cho` は
「区画 × 径数(front / twoSided / nUra / pattern)」の形をすでに持つ。類型ビルダーはこの形を **json に出して
一本に束ねる**。既存ビルダーは、同じ径数を `typology.json` に写して類型ビルダーが同じ区画を建てられた時点で
**同じコミットで削除**する(4 本の指図生成器と同じ扱い — 施主は不要物を残したくない)。

---

## 2. 輪 — 類型の区画には指図も検分の輪も無い

```
普請奉行 ──類型表を起こす──▶ 考証方(表を一度に検める・同定と格式の誤りだけ)
   │                                    │ pass
   ▼                                    ▼
類型ビルダー(区画の形 + 類型表 → 生成) ──▶ 普請検査(隙・境界・埋没・浮きを機械的に測る)
   ▲                                    │
   └── 欠陥はビルダーを直す(同じ類型の全区画に効く) ◀──┘
                                        ▼
                          施主が一括レンダを見る → 承認で完成
                          「この区画は手作りにする」→ 手作りの車線へ移す(区画を typology.json から外し指図を起こす)
```

- 施主が見るのは**類型表と一括レンダの 2 つ**だけ。区画ごとの図・裁定・検分の残は出さない。
- ビルダーの直しは一区画でなく**同じ類型の全区画**に効く。直すほど速くなる。
- 手作りへ移す区画は、`typology.json` から外して `docs/Sashizu/<id>_sashizu.json` を起こす(規則2)。
  逆(手作り → 類型)は施主の一言があれば同じ手順で戻せる。

---

## 3. 類型表 `docs/Sashizu/typology.json` — 唯一の正典

**区画 × 類型 × 径数。** 区画の形は `parcels.json` が正典(規則11)なので**座標は持たない**。
径数は「史料で読める値」だけで、読めない物は `null` にして**類型の既定値**(§4)で埋め、`cert` に確度を書く
(規則7。U のまま既成事実にしない)。

```json
{
 "_": "類型表 — 手作りしない区画の類型と径数。座標は parcels.json。考証方が表ごと一括で検める。docs/typology-builder.md",
 "defaults": { "…": "類型ごとの既定値は §4 の表をここへ写す(生成器の中に埋めない)" },
 "parcels": {
  "sanbezaka_w1": {
   "type": "buke", "rank": "hatamoto_mid", "koku": 800, "yashiki": "kami",
   "front_edge": 0, "gate": "hmon", "enclosure": "nagaya_front+ita", "garden": "small", "kura": 1,
   "cert": {"rank": "B", "koku": "U", "front_edge": "P", "gate": "U"},
   "source": "[切絵図 嘉永] 三べ坂西の旗本並び。石高は未読で類型の既定値"
  },
  "tamachi_chos_1": {
   "type": "machiya", "two_sided": false, "front_edge": 1, "maguchi_ken": 5, "depth_ken": 18,
   "pattern": "auto", "ura_nagaya": 14, "jishinban": true, "kamiyui": true, "inari": true,
   "cert": {"maguchi_ken": "A", "ura_nagaya": "A"}, "source": "[文政町方書上] 四丁目 店借 82/109"
  },
  "sannojubo_parcels_3": {
   "type": "jisha", "kind": "bo", "main_hall_ken": [5, 4], "gate": "kabukimon", "enclosure": "ita",
   "cert": {"kind": "A", "main_hall_ken": "U"}, "source": "[山王社 社僧十坊] 長明院"
  },
  "azukarichi_w1": {
   "type": "kouyuu", "kind": "hoshiba", "surface": "grass", "fence": "yarai",
   "cert": {"kind": "A"}, "source": "[溜池 御預明地・干場]"
  }
 }
}
```

径数の欄(類型ごと。**増やすのは類型の既定値で埋められない史料値が出たときだけ**):

| type | 径数 | 決めるもの |
|---|---|---|
| `buke` | `yashiki`(kami/naka/shimo)・`rank`(daimyo / hatamoto_large / hatamoto_mid / gokenin)・`koku`・`front_edge`・`gate`・`enclosure`・`garden`・`kura` | 門の格式(`estate-types.md` 早見表・[西川1959])、外周(全周長屋 / 前辺長屋+塀 / 塀)、主屋の型(雁行複合 / U字 / 田の字)、蔵の数、庭の有無 |
| `machiya` | `two_sided`・`front_edge`・`maguchi_ken`・`depth_ken`・`pattern`(auto か並び)・`ura_nagaya`・`jishinban`・`kamiyui`・`inari` | 表店の並び(間口で割る)・裏長屋の棟数・番屋と稲荷の有無 |
| `jisha` | `kind`(bo / temple / shake)・`main_hall_ken`・`gate`・`enclosure` | 本堂(または坊の主屋)の間数・門・囲い。⛔ 坊を本堂・山門・鐘楼・墓地つきの寺にしない(考証方 (c)) |
| `kouyuu` | `kind`(azukarichi / hoshiba / hikeshi)・`surface`・`fence` | 地表(草・土)と柵。建物は火消屋敷だけ |

---

## 4. 類型の既定値 — 史料値から引く(規則8。自分の成果物から作らない)

`buke` の石高帯 → 型(`estate-types.md` 早見表と旗本 3 例、[元文3年] の拝領坪数):

| rank | 例 | 門 | 外周 | 主屋 | 蔵 | 庭 |
|---|---|---|---|---|---|---|
| daimyo(上屋敷) | 福井 6,600 坪 | 表門(`Eg.Kmon`)+小門 | 全周長屋(`Eg.Knagaya*`)+隅矢倉 | 御殿複合(`EdoGotenKit`。表向 / 中奥 / 奥向の 3 核) | 2〜4 | 池泉(既定は「ある」) |
| daimyo(中屋敷) | 加納 1,599 坪 | 表門+裏門 | 全周長屋(矢倉なし) | 表 / 奥の 2 核 | 2 | 余白に中規模 |
| hatamoto_large | 吉良 2,559 坪 | 長屋門(`Eg.Hmon`)+番所 | 長屋 30 軒(警護) | 雁行複合+坪庭 | 4 | 坪庭 |
| hatamoto_mid | 武井 412 坪 | 門+板塀 | 前辺長屋+塀 | U 字主屋 | 1 | 裏庭(蔵・井戸) |
| gokenin | 山本 200 坪 | 小門 | 塀+街路側貸家 | 田の字 30 坪 | 0 | 池・築山・花壇 |

`machiya`: 表店は**間口 5 間基準**(`EdoTamachiBuilder` の `S1`/`S2`/`SH` の並び)・奥行 18 間の片側町が既定、
裏長屋は `Eg.Kidobanya` 連結の**スタンドイン**(在庫に専用部材が無い。`edo-zaiko` → 無ければ `edo-buzai`)。
`jisha`: 坊は主屋(5×4 間)+庫裏+板塀+冠木門。`kouyuu`: 草地+矢来。

⛔ 既定値の出典は表の右端の `[ID]` で `sources.md` へ結ぶ。**出典の無い既定値は U** で、類型表の `cert` にそう書く。

---

## 5. 類型ビルダー `EdoTypologyBuilder.cs` — 一本。区画を渡すと建つ

メニュー: `Edo/類型/区画を建てる(選択中の区画)` ・ `Edo/類型/全区画を建てる` ・ `Edo/類型/一括レンダを撮る`。
グループ名は `Edo_Typo_<parcel id>`。**決定的**(同じ区画・同じ表 → 同じ結果。乱数は区画 id を種にする)。

| Stage | 何を | 取り合いの解き方(⛔ 紙で先回りしない・規則5・19) |
|---|---|---|
| 0 面 | 区画内の**自然地形の中央値**を面に採る(規則3・`base_dem.json`)。造成は既定で**しない**。傾きが大きい区画だけ段を 1 つ切り、土留めは `unity-modular-stonewall` の run | 面の高さは地形から。設計値を先に決めない |
| 1 囲い | `EdoParcels.Get(id)` の辺に沿って囲いの run(長屋 / 土塀 / 板塀 / 矢来)を並べる。共有辺は**片側だけ**建てる(隣が先に建てていれば skip。判定は幾何で — 辺番号を信じない) | 隅は出隅の据え方(片面を隣の面に一致させ、もう一辺は端点で合わせる)。ピッチは部材の実寸(`EdoBuild.RB`)。run の端は開口の縁に取り、端数は run の中で吸う |
| 2 門 | `front_edge` の辺の中央(既定)に `gate` の型の門。番所は `hatamoto_large` 以上 | 門は固定・run が可動。門柱の外面と run の妻面を実メッシュで突き付け(隙 0 / めり込み ≤0.05) |
| 3 主屋 | 型(御殿複合 / 雁行 / U字 / 田の字 / 表店列 / 坊)を**区画の内側の矩形**(辺から 6〜8m 引いた最大内接矩形)に置く。江戸間で割る | 棟どうし ≥2.0m。区画・道・水面へ出ない(`EdoGeom.PIP` を OBB の 9 点で) |
| 4 付属 | 蔵・井戸・厩・番屋・稲荷を型の数だけ、主屋の裏(勝手側)に | 主屋と ≥2.0m。区画の中 |
| 5 植栽 | 庭の型に応じて在庫の木(規則10。桜・自作の木は不可)。旗本は庭木 3〜5 本、寺は境内木、公有地は無し | 木は区画・建物・道・水面の中へ入れない(`PIP` と樹冠半径) |
| 6 検査 | 隙 / 境界侵犯 / 埋没・浮き を**同じ Stage で測って刷る**(規則19。0 件でも刷る) | `JointQA` / `GroundQA` の型を共通化して区画 id ごとに件数を返す |

⛔ **座標を C# に書かない**(規則11)。区画は `EdoParcels.Get`、径数は `typology.json`、パスは `EdoAssets.cs`(規則12)。
⛔ 手組み資産(`Ishigaki` / `Nagaya` / `Omotemon`)のある区画は、その資産を**避けて**建てる(規則1)。

---

## 6. 検査と完成 — 区画ごとに測り、一括で見せる

| 項目 | 閾値 | 誰が |
|---|---|---|
| 隙・めり込み・裏表 | 0 件 | Stage 6 → 普請検査が全区画を集計 |
| 境界侵犯(区画 / 道 / 水面 / 隣の建物) | 0 件 | 同上 |
| 埋没・浮き | 埋 >1.0 / 浮 >0.7 が 0 駒 | 同上 |
| 一括レンダ | 真上の正射(全域)+ 街路の目線 3 点 | 普請検査が撮り、**施主が承認** |

完成条件の表(`kansei_gate.py`)は**手作りの敷地**の物。類型の区画は上の 4 行で、`typology.json` の直下に
`"kansei": {"at": "...", "quote": "<施主の発話>"}` を 1 つ持つ(区画ごとには持たない)。
欠陥が出たら**ビルダーを直して全区画を建て直す**(一区画だけ手で直さない — 次の再生成で戻る)。

---

## 7. 実装の段取りと、着手前に施主へ仰ぐこと

段取り(各段が 1 セッション・1 コミットの粒度):

1. **P0 類型表** — 普請奉行が `typology.json` を 88 区画ぶん起こす(手作り候補は `"handmade": true` で印だけ)。
   径数は既存ビルダーと切絵図から写し、読めない物は null+既定値+U。考証方が**一括で 1 巡**。
2. **P1 試作** — `buke` の `hatamoto_mid` 1 区画(三べ坂西の 1 筆が候補)で Stage 0〜6 を通し、一括レンダを施主へ。
3. **P2 buke 全帯** — 石高帯ごとに 1 区画ずつ増やし、既存の街区ビルダーの区画を置き換えて削除。
4. **P3 machiya** — `EdoTamachiBuilder.Cho` の径数を表へ写して置き換え。裏長屋のスタンドインは在庫方 → 部材方。
5. **P4 jisha / kouyuu** — 坊 10 筆・寺 2・社家 1 / 明地 7・火消 1。

【裁定が要る】(着手前。`docs/reporting-protocol.md` の 6 点セットで):

1. **手作りにする敷地の確定** — 候補 6 のうちどれか。候補外に手作りが要る区画はあるか(松平大和守 9,661 坪など)。
2. **試作の 1 区画** — P1 をどの区画で見せるか。
3. **既存の街区ビルダーの扱い** — 置き換え時に削除(推奨・生成器と同じ扱い)か、凍結して残すか。

---

関連: CLAUDE.md 規則2・4・18(二層と完成条件)/ `docs/Sashizu/parcels.json`(区画の正典)/
`Tools/Skills/unity-buke-yashiki/references/estate-types.md`(石高帯の史料値)/ `docs/asset-catalog.md`(在庫)/
`Tools/Sashizu/kansei_gate.py`(手作りの完成条件)/ 裁定の記録 https://claude.ai/artifact/EouMVDWUjrGCaDuZ4tUHVW
