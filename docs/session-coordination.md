# 司令塔 — 複数の Claude Code セッションを同時に走らせる

**2026-08-24 に事故が起きた。** 松平・岡部を作業していたセッションが `git add` を広く打ち、
**別のセッションが編集中だった山王の指図を巻き込んでコミットした**。作業自体は失われなかったが、
山王の改訂が `0f4b9fc` `b16b487` `0891530` という無関係な件名の下に埋まり、
**履歴から追えなくなった**(CLAUDE.md 規則4「経緯は `git log` で追う」の前提が崩れた)。

⚠ **worktree は自動では分かれない。** `.claude/worktrees/` にあるのはサブエージェントが
使った残骸で、通常のセッションは**全部メインのチェックアウトを共有している**。

---

## 作業の型は2つ。始める前にどちらか決める

### ① 指図を書く(Unity を使わない) → **worktree を切る**

```bash
python3 Tools/Session/edo_session.py worktree sanno
cd .claude/worktrees/sanno          # ここで新しいセッションを始める
```

`docs` / `Tools` / `.claude` だけの **sparse worktree**(**12MB・64ファイル**。
Assets の 249MB・825ファイルは来ない)。ブランチも分かれるので、

- 共有ファイル(CLAUDE.md ほか)を巻き込む事故が**構造的に起きない**
- 同じブランチに他人のコミットが載ることも**無い**

⛔ **ここでは Unity は開けない**(パックが gitignore なので Assets が揃わない)。

### ② Unity を触る(実装・計測) → **メインのチェックアウトで、資源を取る**

```bash
python3 Tools/Session/edo_session.py claim sashizu:matsudaira --resources unity --note "松江松平の実装"
```

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

## 手が届かないもの(既知の限界)

- **同じワークツリーを共有したままなら、共有ファイルは守れない。** claim はパス単位なので、
  CLAUDE.md のように**全員が編集するファイル**には効かない。→ worktree を分けること
- **人間が直接打つ git は素通りする。** フックは Claude Code のツール呼び出しにしか掛からない
- **別マシンのセッションは見えない。** 登録簿はこのマシンのファイルシステム上にある
- **Unity の排他は申告制。** Unity 側から「誰が触っているか」は見ていない
