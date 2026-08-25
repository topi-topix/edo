# 司令塔 — 複数の Claude Code セッションを同時に走らせる

**2026-08-24 に事故が起きた。** 松平・岡部を作業していたセッションが `git add` を広く打ち、
**別のセッションが編集中だった山王の指図を巻き込んでコミットした**。作業自体は失われなかったが、
山王の改訂が `0f4b9fc` `b16b487` `0891530` という無関係な件名の下に埋まり、
**履歴から追えなくなった**(CLAUDE.md 規則4「経緯は `git log` で追う」の前提が崩れた)。

⚠ **worktree は自動では分かれない。** `.claude/worktrees/` にあるのはサブエージェントが
使った残骸で、通常のセッションは**全部メインのチェックアウトを共有している**。

---

## 始め方 — 打つのは1行

```bash
python3 Tools/Session/edo_session.py start sanno            # 指図を書く
python3 Tools/Session/edo_session.py start matsudaira --unity  # Unity を触る
```

**司令塔が型を判断して振り分ける。**

- **指図(Unity 不要)** → その屋敷の worktree を**探し、無ければ作って**、作業ディレクトリを返す
- **`--unity`** → メインのチェックアウトに留まり、`unity` 資源を確保する(取れなければ待ち)

⚠ **打ち忘れても効く。** 他のセッションが動いている状態で指図のファイルに触ると、
司令塔が**その場で worktree を用意して回す**。⛔ **cd は要らない** — 返ってきた
worktree の**絶対パス**でファイルを開き、ビルダーもその worktree のものを走らせればよい。

```
/Users/…/.claude/worktrees/sanno/docs/Sashizu/sanno_kosho.md
python3 /Users/…/.claude/worktrees/sanno/Tools/Sashizu/build_sanno_sashizu.py
```

⚠ **一人で作業しているときは回さない。** 競合していないのにメインから追い出すのは邪魔なだけ。
⚠ **Unity を握っているセッションも回さない**(計測・実装のためメインに居るのが正しい)。
⛔ どうしてもメインで書きたいなら `claim --resources main`。

### 指図用の worktree の中身

`docs` / `Tools` / `.claude` だけの **sparse worktree**(**12MB・64ファイル**。
Assets の 249MB・825ファイルは来ない)。ブランチも分かれるので、

- 共有ファイル(CLAUDE.md ほか)を巻き込む事故が**構造的に起きない**
- 同じブランチに他人のコミットが載ることも**無い**

⛔ **ここでは Unity は開けない**(パックが gitignore なので Assets が揃わない)。

### Unity を触るとき

```bash
python3 Tools/Session/edo_session.py start matsudaira --unity --note "松江松平の実装"
```

### Blender で部材を作るとき

```bash
python3 Tools/Session/edo_session.py start goten --blender --note "御殿の屋根"
```

⚠ **Blender 同士は競合しない。** `blender --background` の使い捨てプロセスなので、
Unity のような「実体が1つ」という制約は無い。それでもメインに留まる理由は2つ。

- ⛔ **sparse worktree では成立しない。** `vklib.py` が在庫キットを**メインの絶対パスで
  直書き**しており、そのキット(Japanese Village Kit / Japanese Castle / edogoyomi)は
  **再配布不可で gitignore** なので worktree に来ない。出力先 `Assets/Edo/Models/` も無い
- ⚠ **出力が共有資産。** 同じ部材を2セッションが同時に焼くと**後勝ちで上書き**される。
  `build_goten_roof.py -- rebuild` は `Roofs/` の全数を焼き直すので特に危ない
  → `assets` 資源で直列化する

⚠ 焼いたら Unity で **Edo ▸ 御殿 ▸ …マテリアルをremap** を走らせること
(FBX は材質名しか運ばないので、やらないと白い模型になる)。

⚠ **Unity は実体が1つ**。シーン・プレハブ・地形を共有し、**地形の編集は Undo の外**にある。
`unity` を取れるのは1セッションだけで、取れなければ待つ。

**指図作業の途中で計測が要るとき**も同じ。⚠ **worktree からは Unity を触れない**ので、
メインのチェックアウトのセッションで `--resources unity` を取って測り、**終わったら release する**。
計測は短いので、長時間握らないこと。

```bash
python3 Tools/Session/edo_session.py claim --resources unity --note "山王の地形を測るだけ"
# … 測る …
python3 Tools/Session/edo_session.py release --resources unity
```

---

## 日々の操作

```bash
python3 Tools/Session/edo_session.py status      # 誰が何を押さえているか
python3 Tools/Session/edo_session.py worktrees   # どのワークツリーがどのブランチか
python3 Tools/Session/edo_session.py release     # 自分の claim を全部解く
```

- 屋敷は **`sashizu:<名>`** で名乗る(`docs` と `Tools` の両方を一度に押さえる)
- **名乗り忘れても効く。** ファイルを書いた時点で、そのパスを自動で claim する
- **45分 心拍が途絶えれば自動で失効**する。release を忘れても詰まらない

---

## 何が自動で止まるか

`.claude/settings.json` の `PreToolUse` フックが、ツール呼び出しの前に司令塔へ照会する。
止まるのは**他人の領分に踏み込むときだけ**で、自分の claim なら素通りする。

| 状況 | 挙動 |
|---|---|
| 他のセッションが押さえたファイルを Edit / Write | ⛔ 止める。誰が・何をしているかを出す |
| 他のセッションが Unity 使用中に Unity MCP を叩く | ⛔ 止める。⚠ 読むだけのもの(`read_console` ほか)は通す |
| `git add -A` / `git add .` / `git commit -a` | ⛔ 常に止める。**パスを明示すること** |
| `git reset --hard` / `git clean -f` / `git stash` / `git rebase` / 強制 push | ⛔ 常に止める |
| staging に他人の押さえたファイルが入った状態での `git commit` | ⛔ 止める(事故の再現で検証済み) |
| 自分の領分の作業・パスを明示した git | 素通り |

⚠ **止めるのはコマンド位置に現れたものだけ。** 文字列の中の例示や説明文は拾わない
(そうしないと、この文書を書くだけで作業が止まる — 実際に踏んだ)。

## 引き継ぐとき

```bash
python3 Tools/Session/edo_session.py steal sashizu:sanno --reason "前のセッションが落ちたため"
```

⚠ **奪う前に `status` で心拍を見ること。** 数分以内なら**まだ動いている**。

---

## 設計の約束

- **フックが落ちても作業は止めない。** 例外は握りつぶして素通りさせる
- **生存判定は心拍だけ。** ⛔ pid を見てはならない — フックから呼ばれるスクリプトの親は
  その都度のシェルで、セッションの寿命と無関係(これで claim が即死し、再現テストが素通りした)
- **登録簿は `.git/edo-locks`。** ⛔ worktree ごとに置くと隣の claim が見えず司令塔が死ぬ

## ⚠ 古いワークツリーの写しを読まない・再生成しない

`.claude/worktrees/` には、そのブランチが切られた時点の**全ファイルの写し**がある。
2026-08-25 に `sanno` の写しが main より **11コミット古く**、土井の指図の
**撤回済みの説(S級の引用の取り違えを含む)を保持している**ことが分かった。
併合そのものは安全(片側しか動いていないファイルは巻き戻らない)が、
**そこで生成器を走らせれば古い図が再生産される**。

- ⛔ **他人のワークツリーの `docs/Sashizu/` を読まない。** 正典は main の作業ツリー。
- ⭐ **関門は build 時ではなく merge 時に置く** — 禁句・典拠ID・確度の3検査は非0で止まるので、
  **併合前に生成器を通せば**古い写しは必ず落ちる。禁句表はコミットの性質であって
  ファイルシステムの性質ではない。

## 手が届かないもの(既知の限界)

- ⛔ **claim では「シーンの状態」を守れない。** 司令塔が守るのは**ファイル**であって、
  Unity の地形・シーンという**全員が共有する1個の実体**ではない。
  2026-08-24 に実害が出た: 松平が朝に造成を live terrain へ流し、5時間後に岡部・土井が
  同じ地形を「造成前の現地形」として標本にしたため、**他家の造成が自然地形として指図へ焼き込まれた**
  (土井の DEM は松平区画の68%が松平の設計面の値になっていた)。ファイルの競合は1件も起きていない。
  → **共有の実体から測った値は、正本のファイルへ落として全員がそれを読む。**
  地盤は `docs/Sashizu/base_dem.json`(CLAUDE.md 規則12)。
- **同じワークツリーを共有したままなら、共有ファイルは守れない。** claim はパス単位なので、
  CLAUDE.md のように**全員が編集するファイル**には効かない。→ worktree を分けること
- **人間が直接打つ git は素通りする。** フックは Claude Code のツール呼び出しにしか掛からない
- **別マシンのセッションは見えない。** 登録簿はこのマシンのファイルシステム上にある
- **Unity の排他は申告制。** Unity 側から「誰が触っているか」は見ていない

## 報告・裁定・セッション間の情報共有

→ **[session-board.md](session-board.md)** — 掲示板(`edo_board.py`)と司令塔。
節目・ブロッカー・裁定要請だけ post、他邸に効く変更は起票+相手セッションへ直接メッセージ、
自己検図はユーザー入力なしに3巡まで。
