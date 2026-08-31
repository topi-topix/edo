# 指図（設計図）

**屋敷は Unity で建てる前にここへ設計図を起こし、ユーザーのレビューを受けてから実装する。**
手順は `unity-buke-yashiki` スキル `references/sashizu.md`。

> ⚠ **2026-08-22 に地形を作り直した。造成は消えている。**
> 実装するときは**造成ステージを先に流す**こと。指図の面の高さはそのまま使える(動いたのは面の縁だけ)。
> 山王社だけは山が8m西へ動いたので**座標の引き直し**が要る。→ [`docs/terrain-georef-fix.md`](../terrain-georef-fix.md)

## 決めごと

1. **指図は現況だけを載せる。** 過去の案・撤回した説を本文に残さない。
   経緯は `git log docs/Sashizu/` で追う。積み増すと必ず「何が正か分からない」状態になる（2026-08-20）。
2. **数値は設計値ファイル（`<屋敷>_sashizu.json`）にだけ置く。** HTML も文章もそこから組む。
   表へ書き写した瞬間に二重管理が始まり、片方だけ直る。
3. **面の高さは地形が決める。** 先に高さを決めて地形を合わせない。地形を測り、
   **自然の平場(ベンチ)の高さをそのまま面に採る**。窪みは埋めず一段低い郭にして階段廊下でつなぐ。
   合格の目安は棟が載る所で **|設計面 − 自然地形| ≤ 0.5m**。
4. **指図には現況図・切盛図・断面・動線図を必ず入れる。**
   （現況図=段彩+等高線 / 切盛図=暖色盛土・寒色切土 / 断面=東西南北の格子 / 動線=表向・役方・勝手・奥向）
   → `unity-buke-yashiki` `references/sashizu.md` §3a-§3d。`edo-kenzu` が完備検査で落とす。
5. **造成前の地盤は `base_dem.json` が正典。Unity から採らない。**
   live terrain は自他の造成が乗る作業面で、採る時刻によって値が変わる。各邸の `<屋敷>_dem.json` は
   正本からの切り出しで、`python3 Tools/Sashizu/build_base_dem.py` が書く(手で編集しない)。
   正本自体を作り直すのは `--canon`(`TerrainBackups/` を読むのでメインの作業ツリーでのみ走る)。
   **区画(`parcels.json`)を動かしたら生成器を回す** — 担当区画が切り出しの外へ出ていれば ⛔ で止まり、
   使うべき範囲を数値で出す(⚠ は余白20m未満の警告)。`--fit` で区画+余白40mまで自動で広がる
   (**広げるだけで縮めない**ので既存の値は動かず、セルが増えるだけ)。
   ⚠ 正本は**現代**の地面で、近代造成を含む。江戸期の地盤が要るなら**復元レイヤ**を別に持ち、
   **自分の区画でクリップする**(岡部の `okabe_edo_world.json`)。回転間格子の `<屋敷>_terrain.json`
   は各邸の生成器が作るが、種地はこの正本に揃えること。
6. **順序を守る。**
   `設計(json/md) → 組む → 検図 → レビュー → 実装 → 指図を更新 → 突き合わせて0件 → コミット`
   **実装から指図を生成しない。** 先に図を描く関門が消える。道具が担ってよいのは突き合わせだけ。
   但し書き: 生成器が実装ソース(C#)を読むのは**突き合わせの表を組む目的に限る** —
   設計値を実装から導いてはならない。生成器から `<屋敷>_sashizu.json` への書き戻しも
   **検査結果の記録と正規化に限り**、設計値そのものは常に人が決める。

## 岡部邸の作り（他の屋敷もこの形に寄せる）

| ファイル | 役 | 誰が書くか |
|---|---|---|
| `okabe_sashizu.json` | 設計値の正典 | 人 |
| `okabe_kosho.md` | 文章の部（典拠・決めごと・未解決） | 人 |
| `okabe_sashizu.html` | 上の二つから組んだ図面 | `Tools/Sashizu/build_okabe_sashizu.py` |
| `okabe_dem.json` | 造成前地盤(現代・正典 `base_dem.json` の区画切り出し) | `Tools/Sashizu/build_base_dem.py` |
| `okabe_terrain.json` | 現況地盤の回転間格子標本 | `Tools/Sashizu/build_okabe_edo_dem.py` |
| `okabe_edo_recon.json` | 江戸期復元レイヤの仕様(近代造成を戻す指示) | `Tools/Sashizu/build_okabe_edo_dem.py` |
| `okabe_edo_dem.json` | 江戸期復元地盤の回転間格子 | `Tools/Sashizu/build_okabe_edo_dem.py` |
| `okabe_edo_world.json` | 江戸期復元地盤(世界座標・区画でクリップ)。**隣家の共有辺検査が読む** | `Tools/Sashizu/build_okabe_edo_dem.py` |
| — | 指図と実装の突き合わせ | Unity `Edo ▸ 岡部筑前守上屋敷 ▸ 指図と実装を突き合わせる` |

```bash
python3 Tools/Sashizu/build_okabe_sashizu.py
```

## 基準図

| 図面 | 中身 | Artifact |
|---|---|---|
| [越前福井藩江戸上屋敷](fukui_kamiyashiki.html) | 原図の要約図と、そこから読み取れる組み方。**新しい屋敷を設計するときはまずこれに戻る** | https://claude.ai/code/artifact/77d7df6e-4f21-44f8-b391-68ae1c65e1e5 |

## 屋敷・社ごとの設計図

**状態は「指図」と「実装」の2軸で分けて書く**(2026-08-31 京極セッションの提案・外堀セッションの
「実装済とユーザーが見たは別」を踏まえた改訂)。1軸だと「指図はレビュー待ちだが実装は進んでいる」
邸(松江松平・山王)を表せず、実態とずれていた。

- **指図**: 起案 → 検図中 → 検図済(レビュー待ち) → レビュー済
- **実装**: 未着手 → 実装中 → 実装済(QA未) → 実装済・QA合格(ユーザー確認済)

⭐ **「指図: 検図済 かつ 実装: 未着手」の行が、いま実装に着手してよい屋敷。**

| 屋敷・社 | 地区 | 指図 | 実装 | 図面 | Artifact |
|---|---|---|---|---|---|
| 岡部内膳正 上屋敷（和泉岸和田藩5万3千石） | 山王社北 | レビュー済(検図12巡・当主/年次A)。石段踊り場1件は設計判断でEDO-0018と併せ保留 | **実装済・指図と一致(180項目)** | [okabe_sashizu.html](okabe_sashizu.html) | https://claude.ai/code/artifact/ce6d353b-33ea-4355-aeb4-c5097da69e53 |
| 松平出羽守 上屋敷（出雲松江藩18万6千石・親藩国主） | 山王社北 | 検図中（レビュー待ち） | 実装中(Stage6まで・継続更新) | [matsudaira_dewa_sashizu.html](matsudaira_dewa_sashizu.html) | https://claude.ai/code/artifact/eaba651e-982d-4451-8bb5-d17ba95b8093 |
| 土井大隅守 上屋敷（三河刈谷藩2万3千石・譜代雁間） | 山王社北 | **検図済（レビュー待ち・検図14巡・考証13巡通過・指摘0件）** | **未着手** | [doi_sashizu.html](doi_sashizu.html) | https://claude.ai/code/artifact/539c4b6b-0937-458f-8287-e3200e94f3cf |
| 山王権現社（日枝神社・江戸城の産土神・社領600石） | 永田馬場 星野山 | 検図済（レビュー待ち・_pending 26件残） | 実装中(一部・EDO-0073修正中) | [sanno_sashizu.html](sanno_sashizu.html) | https://claude.ai/code/artifact/b6b4e5cd-8878-4162-be90-4dd4ed706beb |
| 京極備中守 上屋敷（丹後峯山藩1万1千石・菊間詰=譜代格） | 山王坂 | 起案（レビュー待ち・検査10件通過） | 未着手(`EdoKyogokuBitchuBuilder.cs` 無し) | [kyogoku_bitchu_sashizu.html](kyogoku_bitchu_sashizu.html) | https://claude.ai/code/artifact/95578cd4-8016-41a3-9023-dd60e44cc206 |

## 土木の指図(屋敷ではない)

| 普請 | 地区 | 状態 | 図面 | Artifact |
|---|---|---|---|---|
| 溜池堰下流 外堀 掘り直し(Sotobori_00001・00002・00003) | 堰(どんどん)〜幸橋方向 | **実装済(00001 = 2026-08-29 ／ 00002・00003 = 2026-08-31)。⛔ QA不合格1件**(石垣の裏面が駒ごとに空く・郭外SW3c。数値QAは合格していたがレンダで発覚) **・⚠ 施工後の7検査のうち2件が △**(凍結域 K1 に未是正1セル・U14。施工記録の「意図せず動いたセル 0」は偽の合格だった) **・裁定待ち2件**(EDO-0080 = SW2 天端2%埋没・U12 ／ 出隅で躯体の帯が扇形になり駒が埋めない・U11) | [sotobori_sashizu.html](sotobori_sashizu.html) | https://claude.ai/code/artifact/87dd7a78-0238-47c6-917b-107fe4e92dd3 |
| ├ 継ぎ目の折れの検証(00002×00003・新シ橋) | 世界座標 (590, 355) | **決着(2026-08-30)— 実装は史料と一致** | — | https://claude.ai/code/artifact/d864993f-2187-449e-94e8-10649d35c2ff |
| ├ 裁定図(EDO-0046・U9/U1b/U7) | 同上 | U9・U1b・U7① 解決済／U7② は工法 | [sotobori_saitei.html](sotobori_saitei.html) | https://claude.ai/code/artifact/d3c33b29-b81c-49a4-bb98-f799aa557a4f |

**土木は武家屋敷と作りが違う。** 回転間グリッド・室割り・建蔽率は無い。基準は**距離程**で、
図版は 位置と水系／現況／切盛／縦断／横断／取り合い／工区と摺り付け で組む。
段彩のランプも別に持つ(低地の 0〜8m 用。屋敷の 10m 起点のランプでは全部同じ色になる)。

| ファイル | 役 | 誰が書くか |
|---|---|---|
| `sotobori_sashizu.json` | 設計値の正典 | 人 |
| `sotobori_kosho.md` | 文章の部 | 人 |
| `sotobori_dem.json` | 現況地盤と復元の種地(段彩・等高線・切盛の格子) | `Tools/Sashizu/build_sotobori_dem.py` |
| `sotobori_terrain.json` | 縦断・横断・土量・検査の実測 | 同上 |
| `sotobori_sashizu.html` | 上の四つから組んだ図面 | `Tools/Sashizu/build_sotobori_sashizu.py` |
| `sotobori_saitei.json` | **裁定図**の案の定義 | 人 |
| `sotobori_saitei.html` | 裁定図(どこが・どう変わるか)。Artifact https://claude.ai/code/artifact/d3c33b29-b81c-49a4-bb98-f799aa557a4f | `Tools/Sashizu/build_sotobori_saitei.py` |

```bash
python3 Tools/Sashizu/build_sotobori_dem.py      # ⚠ TerrainBackups を読むのでメインの作業ツリーで
python3 Tools/Sashizu/build_sotobori_sashizu.py
python3 Tools/Sashizu/build_sotobori_saitei.py   # ⚠ 同じく TerrainBackups を読む
```

⭐ **裁定が要る所は「裁定図」を別に起こす。** 指図の未解決の欄に文章で書くだけでは
「どこの話か分からない」(2026-08-27 ユーザー指摘)。件ごとに **①全体の中の位置／②拡大平面／
③断面に案を重ねた図／④案の表** の4点セットで出す。⛔ 案の採否が決まったら、決まった案だけを
`sotobori_sashizu.json` へ書き移し、裁定図は畳む。

⚠ `base_dem.json` の範囲(x −800..−330 / z 600..1340)は**外堀を覆っていない**。当面 `build_sotobori_dem.py`
は正本と同じ出自(`ref_height.npy`)から直に切り出す。正本の拡張は `EDO-0014` と併せて起票する。

**寺社は武家屋敷と作りが違う。** `estate-types.md` の建蔽率・拝領坪数・門の格式は適用せず、
「連続御殿複合＋外周長屋帯」も当てはまらない。図版は 社地／境内平面／社殿平面／断面／
参道の割付／囲いの展開／門／山麓の付属（別当・神主・門前町）で組む。

## 図面に入れるもの

1. **敷地全体 配置図** — 区画・段（平場）の高さ・石垣・外周長屋／塀・門・庭園
2. **主郭 御殿平面** — 室群・室名・入側・渡廊下・庭。廊下は**室群の外周を巡る入側**で、群と群は**渡廊下**で結ぶ（中央を突っ切る通路は明治以降の型）
3. **副郭の平面** — 段が分かれる屋敷では郭ごとに
4. **断面** — 段差のある屋敷では、段のつなぎ方（石垣・石段・渡廊下）が平面だけでは読めないため必須
5. **格式の判断と典拠** — 御成セットの有無、門の格式、推定で埋めた箇所の明示

## 作図の作法

- 柱間は**江戸間 1間＝6尺＝1.818m**。建物は桁行×梁間の間数、部屋は畳数（1間²＝2畳）
- 部屋名を図中に書き入れる（甲良家伝来「江戸城本丸御殿図」・「江戸御殿之図」の作法）
- **表向／中奥／奥向**を区分し、境に御錠口を置く
- 方位は「街路の位置が方位より優先」。原図に方位盤が無ければ図面相対（上辺／左辺）で記す
- **矩形の重なりは機械検査してから出す**（総当たりで0件を確認する）

## 生成

`Tools/Sashizu/build_<屋敷>_sashizu.py` が `<屋敷>_sashizu.json` と `<屋敷>_kosho.md` から一枚に組む
(5邸: okabe / matsudaira / doi / sanno / kyogoku_bitchu)。地盤側は `Tools/Sashizu/build_base_dem.py`(切り出し)と
`Tools/Sashizu/build_<屋敷>_edo_dem.py`(復元レイヤ・間格子。現状 okabe / doi / kyogoku_bitchu のみ)が書く。
**生成器は実装を読まない。** 座標は世界座標（Unity のシーン座標）から `Proj` / `Grid` で
直に変換しているので、図面と実装がズレない。

- `Proj` … 世界座標 → SVG px（z は北が上なので Y だけ反転）
- `Grid` … 間グリッドの指数 (u,v) → 世界座標。原点と向きは json の `grid` が持つ

⚠ SVG の `<text>` に markdown は効かない（`**` が literal で出る）。
⚠ `text-anchor` は **style で出す**。クラス側の `text-anchor:middle` は CSS 規則なので
presentation attribute より強く、属性で書くと効かない（左端の注記が中央寄せされて切れる）。
