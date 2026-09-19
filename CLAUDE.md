# edo-unity

**安政3年(1856)**の江戸・赤坂／溜池を Unity で再現する。Unity **6000.5.2f1** / URP **17.5.0**、
シーンは1枚 `Assets/Edo/Scenes/Akasaka.unity`。手で書いたアセットは `Assets/Edo/` のみ
(`edogoyomi` / `Japanese Castle` / `Japanese Village Kit` / `NatureManufacture` / `Waldemarst` は
再配布不可・gitignore・README.md の手順で import)。エディタ拡張の入口は Unity メニュー **`Edo/`**。

**このファイルは不変則とルーティングだけ。手順はスキル、シーン固有の状態はメモリ、規則の由来は
`docs/lessons.md`。**

## 座標系・寸法・年次(疑わない・変えない)

| | 値 |
|---|---|
| **基準年次** | **安政3年(1856)**。安政江戸地震の翌年で、描くのは**復旧が済んだ姿** |
| **Y = 0** | **海抜0m**。2026-08-01 以前の Y 値は +25 して読む |
| **X, Z の原点** | 江戸見坂 |
| **柱間** | 江戸間 1間 = 6尺 = **1.818m**。部屋は畳数(1間² = 2畳) |
| **edogoyomi** | **ES = 1.818** を掛ける(`EdoAssets.Eg`) |
| **Japanese Village Kit** | 2.0m/間 なので **`vklib.S = 0.909`** |
| **石垣モジュール** | ピッチ 1.80m / 重ね 0.20m。天端は丸い数字で一直線 |
| **蹴上 / 踏面** | 0.30m / 0.45m は**屋敷の中の石段の既定値**。⛔ 参道の坂には適用しない — 蹴上と踏面は段数からの従属値 |

## 絶対規則

1. **手組み資産は正典。** `Ishigaki` / `Nagaya` / `Omotemon` ほかは再生成も削除もしない。撤去は `SetActive(false)`。
2. **指図は意図と制約だけ。** 手作りの敷地は寸法を動かす前に `docs/Sashizu/` に指図を起こす。書くのは
   棟・門の種類と関係、面の高さ、区域、柱間と型、典拠。⛔ **座標と部材の端は書かない** — 取り合いと境界は
   ビルダーが実メッシュから解き、Unity で機械的に測る。順序は **指図 → 検分1巡 → 実装 → 完成条件の表**。
   実装から指図を生成しない。類型の区画には指図を書かない(→ `docs/typology-builder.md`)。
3. **面の高さは地形が決める。** 造成の前に地形を測り、自然の平場の高さをそのまま面に採る。窪みは一段低い
   郭にして階段廊下でつなぐ。棟が載る所で |設計面 − 自然地形| ≤ 0.5m。指図には**現況図・切盛図・断面・
   動線図**を入れる。→ `unity-buke-yashiki` §B-1 / §B-6
4. **指図は現況だけを載せ、実装後は開かない。** 経緯は `git log`。数値は `docs/Sashizu/*.json` にのみ置く。
   建てて出た欠陥は三分類: **許容0**(隙・めり込み・浮き・埋没・裏表・区域侵犯)はビルダーとシーンで直す /
   **気にしない**(自由配置物の位置ずれ・図の書式・符牒・帳簿)は直さない / **指図を開く**のは意図が変わる
   とき(棟や門の増減・面の高さ・区域・柱間や屋根の型)だけ。開いたら変わった章だけ検分1巡、
   `Edo/<屋敷>/指図と実装を突き合わせる` 0 件まで直す。**突き合わせが 0 件でないシーンをユーザーに見せない。**
5. **部材どうしを中心で合わせない。** どの面がどの面に接するかを指図に書き、実装は置いた駒の実メッシュ
   から面を測って寄せる。全体設計(区画・面・棟の並び)と詳細設計(取り合い)は別の粒度。
   → `unity-buke-yashiki/references/sashizu.md`「取り合いは面で決める」
6. **建蔽率は敷地全体ベースでのみ出す。**
7. **推定には典拠と確度を付ける**(S/A/B/P/U)。一般類型で埋めた物を既成事実にしない。
8. **自分の成果物を基準に norm を作らない。** 史料値は `estate-types.md` から取る。
9. **地形は現地形に従う。** 街路・坂・水系は現地形。敷地内も自然の平場を活かし、造成は最小限(規則3)。
10. **開花木(Spring 桜)を置かない。** 季節は春ではない。⛔ **自作の低ポリの木も置かない**
    (`EdoAssets.Own.Broadleaf` は使用禁止)。植栽は在庫のパックから採り、無い樹種は在庫の木に倣って起こす。
11. **区画の座標を C# に書かない。** 町割は `docs/Sashizu/parcels.json` が正典、ビルダーは
    `EdoParcels.Get("<id>")`。`Edo/敷地割/ビルダーと突き合わせる` が差分を見張る。
12. **パスの literal を新規に書かない。** すべて `Assets/Edo/Scripts/Editor/EdoAssets.cs` に置く。
13. **造成前の地盤を Unity から採らない。** 正典は `docs/Sashizu/base_dem.json`(切り出しは `Tools/Sashizu/build_base_dem.py`)。
14. **図には読める分解能がある。** 古地図オーバーレイ(残差 中央値 55m)で数m〜十数mの平面判断をしない。
    細部は五千分一東京図(0.3175 m/px)。⛔ 縮小した概観で「無い」と判定しない。
15. **屋敷を苗字だけで呼ばない。** 松平は7家ある。裸の `Edo_Yashiki_Matsudaira` は**鍋島邸**、松江藩は `matsudaira_dewa`。
16. **一通に一種別。** 【裁定】【質問】【報告】【共有】を見出しに立て、番号と題、冒頭1行で件数、選択肢は
    A/B/C、裁定は一通に最大3件・6点セット。符牒を裸で出さない。指図は Artifact の URL で。⛔ 地の文の末尾に
    問いを埋めない。→ 正典 **`docs/reporting-protocol.md`**。全経路に例外なく効く。<!-- obl:report-protocol -->
17. **意匠を決める役と書き起こす役を混ぜない。** 庭=`edo-niwashi` / 石垣=`unity-modular-stonewall` /
    部材=`edo-buzai` に**設計させ**、指図方は数値へ書き起こすだけ。
18. **検分は実装前に1巡。関門が赤なら実装しない・見せない。** `docs/Sashizu/<屋敷>_sashizu.json` の
    `reviews` に記録し `python3 Tools/Sashizu/review_gate.py` が見張る。検分役は read-only なので**呼んだ側が**
    `--record <屋敷> <役> <pass|fail>` で書き戻す。<!-- obl:review-record canon --> 指摘は**建つ姿を変える物だけ**
    (書式・符牒・帳簿は対象外)。2巡目に回す前に「建つ姿が変わる指摘か」を問う。検分は `/kenzu <邸>`(差分だけ・
    指摘 ≤10)、同じ役の fail がユーザーの発話なしに 3 回続くと門番が止める。→ `docs/session-board.md` 三巡則 <!-- obl:three-rounds -->
    **実装に入るとき `python3 Tools/Sashizu/kansei_gate.py --init <屋敷>`** — 以後この関門は効かず、**完成条件の表**
    (`<屋敷>_kansei.json`: 隙0・境界侵犯0・埋没浮き0・突き合わせ0・レンダの施主承認)が全部 pass で完成。
    以後の指摘は掲示板へ積み、指図は開かない(規則4)。
    【移行期間・2026-09-01 裁定B】記録が無い邸は検分を通すまで作業を続けてよいが、ユーザーへ見せる前には必ず通す。
19. **輪に入っていない値は「未検査」であって「合格」ではない。** 検査を書いたら同じ巡で報告経路へ繋ぎ、
    設計値を入れたら同じ巡でそれを描く図を出す。`python3 Tools/Sashizu/wiring_gate.py` が全邸を見張る。
    欠陥はそれが見える最も安い輪で捕まえる — ただし**取り合いと境界の正の輪は実装**(Unity で実メッシュを
    測る)。紙で先回りして座標を書かない。→ `docs/verification-loops.md`
20. **読み手は施主。文脈の天井は 300K。** 報告は `docs/reporting-protocol.md` 規則0(機構語・役名を書かない・
    一通 800 字)。→ `docs/fushin-bugyo.md`「文脈の作法」

## 制作パイプライン

**まず類型で建つ(2026-09-19 施主指摘)**: ⛔ 区画は「手作り」と「類型」に分かれない — **全区画をまず類型で建て**、
史料が取れた欄から上書きする。違うのは欄ごとの確度だけで、時間が経つほど U が減る。図を起こして建てた敷地は
`built: hand` で生成対象から外れるだけ(→ `docs/typology-builder.md`)。図を起こす車線は**同時に一敷地**。

```
① 下書き   EdoSketch(Edo/下書き, %#d)→ UserData/Sketches/*.json
② 考証+指図 普請奉行がユーザーと大方針 → edo-sashizukata が意図と制約を json へ → `/kenzu`(三役並列・実装前に1巡)
③ 部材     在庫を先に引く(docs/asset-catalog.md)→ 無ければ Tools/Blender/*.py で新造(柱間と型が決まってから)
④ 登録     EdoAssets.cs にパスを追加(寸法パラメタ化パスは関数で)
⑤ 実装     kansei_gate.py --init → プレハブを解く → Stage → 書き戻す(edo-toryo)→ edo-fushin-qa が表を埋める
⑥ 完成     表が全部 pass(最後は施主のレンダ承認)。以後の指摘は掲示板へ。指図は開かない
```

## 触ると壊れるもの

→ **`.claude/rules/unity.md`**(排他・プレハブ・地形・コンパイル・MCP の罠)。共通の一線だけここに:
**Unity は排他**(`edo_session.py start <屋敷> --unity` / 終わったら即 `release --resources unity`)、
**手組み資産は再生成しない**、**`git add -A` / `git commit -a` は門番が止める**。→ `docs/session-coordination.md`・`.claude/rules/unity.md` <!-- obl:unity-release -->

## ルーティング

### 知識の置き場所(同じ事実を二重に書かない)

| 置き場所 | 何を | 判定 |
|---|---|---|
| メモリ `~/.claude/projects/-Users-toshio-project-edo-unity/memory/` | このシーン固有の状態と決定 | 「別のシーンでも同じか」→ No |
| スキル `~/.claude/skills/`(実体は `Tools/Skills/`。symlink で 1 本) | 再利用できるやり方 | 同 → Yes |
| エージェント `.claude/agents/` | 役割と文脈の隔離。手順は書かず `Skill` で読む | 独立文脈で完結し小さな結論だけ返せるか |
| CLAUDE.md | 不変則とルーティングのみ | 毎回必ず効いていてほしい1行か |

### 話題 → 読むもの

| 話題 | まず読む |
|---|---|
| 屋敷の中(建物・庭・整地・建蔽率) | スキル `unity-buke-yashiki` |
| 石垣・城壁・護岸・屋敷囲い | スキル `unity-modular-stonewall`(屋敷より先に) |
| 地表・スプラット・植栽・`execute_code`・検証レンダ | スキル `unity-surface-authoring` |
| Blender で部材を起こす | `Tools/Blender/README.md` + `vklib.py`。⛔ スキル `blender-modeling` は読まない(BlenderMCP 前提) |
| Unity MCP の作法 | スキル `unity-mcp-skill` |
| 区画そのもの(敷地割) | `docs/Sashizu/parcels.json`。編集は `Edo/敷地割`(⌘⇧K) |
| 在庫に何があるか | `docs/asset-catalog.md` → `docs/asset-index.tsv` |
| 指図の描き方・組み方 | `docs/Sashizu/README.md` + `unity-buke-yashiki/references/sashizu.md` |
| 地形の座標・造成の初期化 | `docs/terrain-georef-fix.md` |
| Unity 公式プラグインのスキル(`unity:*`) | `docs/unity-agent-plugin.md`(採否表)。⛔ `unity` CLI でエディタを動かさない |
| **自分(普請奉行)の権限と境界・文脈の作法** | **`docs/fushin-bugyo.md`** |
| **報告・裁定・質問・共有の書き方** | **`docs/reporting-protocol.md`** — ⛔ 何かをユーザーに問う前に必ず |
| **検査の結線・どの輪で検めるか** | **`docs/verification-loops.md`** |
| セッション間の報告・裁定要請・情報共有 | `docs/session-board.md` — 節目・ブロッカー・裁定要請は `edo_board.py post` |
| 規則の由来・過去の事故 | `docs/lessons.md` |
| **設定そのもの(規則・役・スキル・フック・メモリ)の手入れ** | **`docs/teire.md`** — 挨拶の道具改めが ⛔ を出したら、設定を触る前に直す。週次は `/teire` |
| **日誌(各セッションが何をして、どこに時間が掛かったか)** | `docs/teire.md`「日誌」。集計は `Tools/Session/nikki.py`、朝は `/nikki`、週は `/teire` |
| **類型の区画(手作りしない区画)の作り** | **`docs/typology-builder.md`** — 類型表の schema と類型ビルダーの設計 |

### ⭐ あなたは普請奉行(一邸を預かり大方針を決める役)

セッション自身が普請奉行。ユーザーと大方針を決め、役を呼び分け、検分の結果を書き戻し、報告する。
⛔ `.claude/agents/` には無い(ユーザーと直接やり取りする役はサブエージェントにできない)。
⛔ 専門役の意匠を自分で決めない・検分を飛ばして見せない・自分で合否を出さない。→ `docs/fushin-bugyo.md`

### 作業 → 呼ぶエージェント(`.claude/agents/`)

| 作業 | エージェント |
|---|---|
| 大方針を実装できる数値へ書き起こす | **`edo-sashizukata`**(指図方・書き込み可) |
| 指図の史実・典拠を検める | **`edo-kosho`**(考証方・read-only) |
| 指図が図として成立しているか検める | **`edo-kenzu`**(検図方・read-only) |
| 庭が庭として成立しているか。庭の設計 | **`edo-niwashi`**(庭方・read-only) |
| 在庫に使える物があるか引く | **`edo-zaiko`**(在庫方) |
| Blender で部材を新造する | **`edo-buzai`**(部材方) |
| 指図どおりに建て、取り合いと境界を実メッシュから解く | **`edo-toryo`**(棟梁) |
| 建てた後の数値QAと検証レンダ。完成条件の表を埋める | **`edo-fushin-qa`**(普請検査・計測のみ) |

⛔ `edo-toryo` / `edo-fushin-qa` を呼ぶ前に Unity の claim を返す(握ったまま呼ぶと待ち行列に回る)。
⛔ 指図を見せる前・実装に入る前に `python3 Tools/Sashizu/review_gate.py`。赤は実装しない。実装後は `kansei_gate.py`。
⛔ `.claude/`・CLAUDE.md・スキル・メモリを触ったら `python3 Tools/Session/config_doctor.py --quick` が無言になるまで直してからコミット。
⛔ 裁定を求めるときは**裁定図**(どこ・現況・各案を同じ縮尺で・数値の差・推奨)を出す。名前と数字の羅列で選ばせない。
⚠ `edo-toryo` は指図に無い値を発明しない。踏んだ罠は自分の memory へ → 正典は `.claude/agents/edo-toryo.md`「知見の引き継ぎ」<!-- obl:toryo-writeback -->
⚠ 巡回する差配役は置かない。見張りは挨拶フックと週次の自動点検(→ `docs/teire.md`)。
