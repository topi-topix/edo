# 門番 — 複数の Claude Code セッションを同時に走らせる

**2026-08-24 に事故が起きた。** 松平・岡部を作業していたセッションが `git add` を広く打ち、
**別のセッションが編集中だった山王の指図を巻き込んでコミットした**。作業自体は失われなかったが、
山王の改訂が `0f4b9fc` `b16b487` `0891530` という無関係な件名の下に埋まり、
**履歴から追えなくなった**(CLAUDE.md 規則4「経緯は `git log` で追う」の前提が崩れた)。

⚠ **worktree は自動では分かれない。** `.claude/worktrees/` にあるのはサブエージェントが
使った残骸で、通常のセッションは**全部メインのチェックアウトを共有している**。

---

## ⛔ 身元は毎回 `--session <短縮ID>` で明示する

**Bash の作業ディレクトリはターンをまたぐと元(メインのチェックアウト)へ戻ることがある。**
`cd` した直後の数コマンドは worktree で動いても、次のターンで `pwd` を取るとメインに戻っている
——これは Claude Code のシェルの仕様で、当プロジェクトの門番では直せない。

`edo_session.py` は `EDO_SESSION_ID`(環境変数)が無いとき、**その時点の cwd** から身元を
推測する。**フック(`edo_guard.py`)は自分自身の照会にしか `EDO_SESSION_ID` を渡さず、
Bash が実際に実行するコマンドの環境には注入しない。** つまり明示しない限り、cwd がメインへ
戻った瞬間に**別のセッションの claim へなりすます**か、該当する claim が無ければ**新しい
空の身元**になる(2026-08-31、京極・土井の両セッションで実際に claim が消えて見えた)。

**対策 — 毎回、次の形で打つ:**

```bash
python3 Tools/Session/edo_session.py --session <status の ▶ 行に出る短縮ID> claim ...
python3 Tools/Session/edo_session.py --session <短縮ID> release ...
python3 Tools/Session/edo_session.py --session <短縮ID> commit ...
```

`start` で最初に発行された短縮ID を控えておき、以後すべての呼び出しに付ける。
`status` だけは省略しても壊れない(読むだけの照会は身元不明でも通す)。

---

## ⛔ worktree の Tools/Session/ は古い。`edo_session.py`/`edo_board.py` は main の絶対パスで呼ぶ

sparse worktree には `Tools/` も入るので `python3 Tools/Session/edo_session.py ...` は**動いてしまう**
——動くのに、**main へマージするまで古いコード**を実行する。エラーにならないので気づきにくい。

2026-08-31、これで実際に壊れた: worktree 内の `edo_session.py` には `wait`/`unwait` サブコマンドが
無く(`9677eea` 以降に main へ入った)、身元判定の是正(`81a5250`)も届いていなかった。
`start` は worktree の古い判定で「使用中」、`wait` は同じ worktree の古い版で「invalid choice」——
**同じセッションの中で、コマンドごとに違う結果が返った**(松平・外堀の両セッションが発見・EDO-0076)。
`edo_board.py` の敷地の名簿は 2026-09-01 に**指図の実体から毎回引く**ようになった
(それまでは固定の tuple で、京極備中守・丹羽左京・内藤紀伊は `post --estate <邸>` が弾かれ、
**掲示板に一言も起票できなかった**)。⚠ ただし worktree 側の古い写しを走らせれば古い名簿のままなので、
main の絶対パスで叩く原則は変わらない。

フック(`edo_guard.py`/`edo_greet.py`)は 2026-08-31 に、git の common-dir から main の絶対パスを
解決して**常に main の Tools/Session/ を実行する**よう直した。**手で叩くときは同じことを自分でやる**:

```bash
# ⛔ worktree の cwd から相対パスで叩かない(古いコードが動く)
python3 Tools/Session/edo_session.py status

# ⭕ main の絶対パスで叩く(worktree の cwd からでもこれでよい)
python3 /Users/toshio/project/edo-unity/Tools/Session/edo_session.py status
python3 /Users/toshio/project/edo-unity/Tools/Session/edo_board.py list
```

`wait`/`unwait`/`--session` など聞き覚えのないサブコマンドが `invalid choice` で弾かれたら、
まずこれを疑う——**バグではなく worktree の Tools/ が古いだけ**であることが多い。

---

## 始め方 — 打つのは1行

```bash
python3 Tools/Session/edo_session.py start sanno            # 指図を書く
python3 Tools/Session/edo_session.py start matsudaira --unity  # Unity を触る
```

**門番が型を判断して振り分ける。**

- **指図(Unity 不要)** → その屋敷の worktree を**探し、無ければ作って**、作業ディレクトリを返す
- **`--unity`** → メインのチェックアウトに留まり、`unity` 資源を確保する(取れなければ待ち)

⚠ **打ち忘れても効く。** 他のセッションが動いている状態で指図のファイルに触ると、
門番が**その場で worktree を用意して回す**。⛔ **cd は要らない** — 返ってきた
worktree の**絶対パス**でファイルを開き、ビルダーもその worktree のものを走らせればよい。

```
/Users/…/.claude/worktrees/sanno/docs/Sashizu/sanno_kosho.md
python3 /Users/…/.claude/worktrees/sanno/Tools/Sashizu/build_sanno_sashizu.py
```

⚠ **一人で作業しているときは回さない。** 競合していないのにメインから追い出すのは邪魔なだけ。
⚠ **Unity を握っているセッションも回さない**(計測・実装のためメインに居るのが正しい)。
⛔ どうしてもメインで書きたいなら `claim --resources main`
(⚠ 2026-09-01 まで「不明な資源」で**弾かれていた** — 門番自身が案内する逃げ道が塞がっていた。
`main` は排他ではない名乗りで、複数のセッションが同時に持ってよい)。

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

#### ⛔ 終わったら必ず返す — 握りっぱなしにしない

```bash
python3 Tools/Session/edo_session.py release --resources unity
```

**Unity の作業が一区切りついたら、セッションを続けるかどうかに関わらずその場で返す。**
考証を調べる・指図を直す・報告を書く、といった Unity を使わない時間に握り続けない。

⚠ **心拍では「終わったか」を判定できない。** 心拍は Write/Edit/Bash でも更新されるので、
Unity を握ったまま別の作業をしているセッションの claim は**永久に生き続ける**。TTL を
縮めても解けない(2026-08-30 ユーザー指摘「作業が終わっているのに unity をつかみ続けて、
他のセッションがさわれなくなる」)。そのため門番は**資源ごとの最終使用時刻を心拍と別に持つ**:

- `status` に `資源: unity(最終使用 25分前 ⚠放置)` と出る
- **20分** 使われていない unity は空きとみなし、待っているセッションが**自動で引き取る**
  (掴んだセッションが生きていても明け渡させる)

#### 使いたいのに埋まっているとき — 待ち行列に並ぶ

```bash
python3 Tools/Session/edo_session.py wait --resources unity --note "土井の接地QA"
```

⛔ **早い者勝ちにしない。** 空いた瞬間に別のセッションが割り込むと待っていた側が延々待つので、
門番は**先頭の1名にだけ15分の予約**を出し、その間は他が取れない。
⚠ 2026-09-01 まで、予約を見ていたのは **Unity MCP を叩いた経路だけ**で、`start --unity` と
`claim --resources unity` は**素通りで横取りできた** — 規則どおり並んだ側が、後から来た
`start --unity` に追い越されていた。いまは3つの入口が同じ関数(`take_resource`)を通る。
⭐ 保持者が心拍ごと落ちた場合も、次の `status` で先頭に予約が出る(`release` を打たずに
落ちると誰も引き渡さなかった)。
Unity MCP を叩いて弾かれた場合は**自動で行列に並ぶ**(`wait` を打ち忘れても効く)。
降りるときは `unwait --resources unity`。順番は `status` に出る。

⛔ **返した側は次の人へ連絡する義務がある。** `release` すると門番が
「次は誰か」を表示するので、`ListAgents` で相手を探し `SendMessage` で
「unity が空きました。予約は15分です」と伝える。**連絡しないと相手は待ち続ける。**

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

- 屋敷は **`sashizu:<名>`** で名乗る(`docs` と `Tools` の両方を一度に押さえる)。
  ⚠ **名は官位まで**(`matsudaira_dewa` / `kyogoku_bitchu` / `niwa_sakyo`)。2026-09-01 まで
  門番は名前を最初の下線で切っており、`start kyogoku_bitchu` の名乗り `sashizu:kyogoku_bitchu` と
  ファイルから導いた `sashizu:kyogoku` が**永久に一致せず、下線を含む名の邸は指図が
  1バイトも守られていなかった**。いまは実在する指図の名前から最長一致で採る
- ディレクトリを名乗れば**その下のファイルも守る**(2026-09-01 まで完全一致か glob だけで、
  `claim Tools/Session` は何も守っていなかった)
- **名乗り忘れても効く。** ファイルを書いた時点で、そのパスを自動で claim する
- **45分 心拍が途絶えれば自動で失効**する。release を忘れても詰まらない

---

## 何が自動で止まるか

`.claude/settings.json` の `PreToolUse` フックが、ツール呼び出しの前に門番へ照会する。
止まるのは**他人の領分に踏み込むときだけ**で、自分の claim なら素通りする。

| 状況 | 挙動 |
|---|---|
| 他のセッションが押さえたファイルを Edit / Write | ⛔ 止める。誰が・何をしているかを出す |
| **他のセッションが押さえたファイルを Bash で書く**(`sed -i` / `>` `>>` / `tee` / `mv` / `cp` / `rm`) | ⛔ 止める(2026-09-01 に塞いだ穴。それまで**素通りだった**) |
| **他のセッションが押さえた屋敷の生成器を走らせる**(`python3 …/build_<邸>_sashizu.py`) | ⛔ 止める。生成器は指図を丸ごと書き直すので相手の編集が消える |
| 他のセッションが Unity 使用中に Unity MCP を叩く | ⛔ 止める。⚠ 読むだけのもの(`read_console` ほか)は通す |
| `git add -A` / `git add .` / `git commit -a` | ⛔ 常に止める。**パスを明示すること** |
| `git reset --hard` / `git clean -f` / `git stash` / `git rebase` / 強制 push | ⛔ 常に止める |
| staging に他人の押さえたファイルが入った状態での `git commit` | ⛔ 止める(事故の再現で検証済み) |
| 自分の領分の作業・パスを明示した git | 素通り |

⚠ **止めるのはコマンド位置に現れたものだけ。** 文字列の中の例示や説明文は拾わない
(そうしないと、この文書を書くだけで作業が止まる — 実際に踏んだ)。
Bash の書き込み先を見るときも **heredoc の中身は落としてから**走査する
(`cat > note.md <<EOF` の本文に他人のパスが出てきても止めない)。

⚠ **判定の規則は Edit と同じ** — 他人の claim を覆うときだけ止まる。無主のパス・自分の領分・
scratchpad は素通りする。⛔ **「Bash なら通る」を回避路として使わない** — 塞いだのは、
エージェントが `sed -i` や heredoc で編集する経路が日常化していて、**門番が守っていると
書いてある区画が実際には守られていなかった**ため(2026-09-01 の点検)。

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
- **登録簿は `.git/edo-locks`。** ⛔ worktree ごとに置くと隣の claim が見えず門番が死ぬ

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

- ⛔ **claim では「シーンの状態」を守れない。** 門番が守るのは**ファイル**であって、
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

→ **[session-board.md](session-board.md)** — 掲示板(`edo_board.py`)。
節目・ブロッカー・裁定要請だけ post、他邸に効く変更は起票+相手セッションへ直接メッセージ、
自己検図はユーザー入力なしに3巡まで。
