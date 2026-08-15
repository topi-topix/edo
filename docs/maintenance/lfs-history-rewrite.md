# LFS 履歴の掃除（作業計画・引き継ぎ用）

作成 2026-08-15。**2026-08-15 に実施完了**（結果は §6）。
手順は次回のためにそのまま残してある。踏んだ罠は Step 0 / Step 2 の ⚠ に追記済み。
関連メモリ: `akasaka-scene-bloat` / `edo-github-repo`

---

## 1. なぜやるか

GitHub `topi-topix/edo`（Public）の LFS 保存量が**無料枠 1 GiB に対して 7.57 GB**。
超過分は課金対象（データパック or 従量課金。請求状況はユーザーが
<https://github.com/settings/billing> で要確認）。

### 実測（2026-08-15、`main` の履歴が抱える LFS 実体）

| 中身 | 保存量 | 本数 |
|---|---|---|
| `Assets/Edo/Scenes/Akasaka.unity` | **6.46 GB** | **55本** |
| `Assets/Edo/Terrain/*.asset` | 1.00 GB | 94本 |
| その他（Models / Materials / Textures ほか） | 0.11 GB | 130本 |
| **合計** | **7.57 GB** | 279本 |

必要なのは**各パスの最新1本だけ（合計 約0.26 GB）**。残りはすべて過去バージョン。

### 経緯（同じ轍を踏まないために）

2026-08-09 の `ac5c73c` で「`.git` の肥大化対策」として `Akasaka.unity` を LFS に移した。
`.git` のオブジェクトストアは確かに止まったが、**LFS は差分を取らずバージョンごと丸ごと保存する**ため、
肥大化の場所が `.git` から LFS へ移っただけだった。以後54バージョン＝6.46 GB。

**シーンは現在 246 MB**（うち 195 MB が **79,547個の PrefabInstance ブロック**）。
1コミットごとに約250 MB が保存量に乗る。なお 246 MB は GitHub の通常 git オブジェクトの
上限 100 MB を超えるので、**LFS を外す選択肢は無い**。

---

## 2. ゴールと限界

- **ゴール**: remote の LFS 保存量 7.57 GB → **0.3〜0.5 GB**（無料枠内）
- ⚠ **この作業は蛇口を閉めない。** 246 MB のシーンを毎セッション commit する限り、
  **約4コミットで再び 1 GiB を超え、約28セッションで 7 GB に戻る**。
  本命の対策は別紙 **A（シーンを地区ごとの additive scene に分割）**。この掃除はその前後に一度やる止血。

---

## 3. 前提と制約（着手前に必ず読む）

- **GitHub は履歴を書き換えても LFS オブジェクトを自動では消さない。**
  ローカルで履歴を書き換えて force push しても、**GitHub 側の 7.57 GB は残る**。
  実際に消すには次のどちらかが要る:
  - (a) **リポジトリを削除して作り直す**（2026-08-02 に一度実施した前例あり）
  - (b) GitHub サポートに LFS オブジェクトの purge を依頼する
  → **どちらもユーザーの操作・判断が要る。エージェントが勝手にやらないこと。**
- **ディスクの空きが 26 GiB しかない**（リポジトリは 37 GB、うち `.git` 19 GB・`Library` 11 GB）。
  **フルコピーのバックアップは入らない。** バンドル方式を使う（下記 Step 0）。
- **`archive/local-history-2026-08-02` ブランチは絶対に触らない。**
  旧137コミットが**ローカルにしか無い**（push していない）。
  ここが抱えるサードパーティ製パック約6.9 GB の LFS 実体もローカルのみ。
  → 書き換えの対象は **`main` だけ**。`.git/lfs/objects` は消さない。
- `feat/goten-watariroka` は `main` にマージ済み（`32c7e0c`）。書き換え前に削除してよい。

---

## 4. 手順

### Step 0 — バックアップ（必須）

```bash
cd /Users/toshio/project/edo-unity
git bundle create ~/edo-history-backup-$(date +%Y%m%d).bundle --all
git bundle verify ~/edo-history-backup-$(date +%Y%m%d).bundle
```

バンドルは git オブジェクトのみ（≒1 GB）。**LFS 実体は含まれない**が、
`main` 側の LFS 実体は GitHub にも `.git/lfs/objects` にもあるので、
`.git/lfs/objects` を消さない限り復元できる。

現在のシーンと地形も退避しておく（書き換えで作業ツリーが reset されるため）。
⚠ **シェルの `*` はサブディレクトリを拾わない。** 落とすパスと退避するパスを取り違えると
`details/` 配下が退避漏れになる（2026-08-15 に実際に踏んだ。下の Step 2 の警告も読むこと）:

```bash
mkdir -p ~/edo-keep
cp Assets/Edo/Scenes/Akasaka.unity ~/edo-keep/
rsync -R Assets/Edo/Terrain/**/*.asset Assets/Edo/Terrain/*.asset ~/edo-keep/   # zsh。パス構造ごと保存
```

### Step 1 — 道具を入れる

```bash
brew install git-filter-repo
```

### Step 2 — 履歴から重いパスを落とす

**方針**: コミット履歴（指図→実装の経緯が全部入っている）は残し、
**重いバイナリの過去バージョンだけ**を落とす。最新版は後から1コミットで入れ直す。

```bash
cd /Users/toshio/project/edo-unity
git branch -D feat/goten-watariroka          # マージ済み
git filter-repo --force --refs main --prune-empty=never \
  --path Assets/Edo/Scenes/Akasaka.unity \
  --path-glob 'Assets/Edo/Terrain/*.asset' \
  --invert-paths
```

⚠ **踏んだ罠が2つある（2026-08-15）。両方とも上のコマンドには反映済み。**

1. **`--prune-empty=never` は必須。** 付けないと「バイナリだけを変更していたコミット」が
   空コミット扱いで自動削除され、**14コミット（139→125）が消えた**。
   消えたのは「三屋敷の敷地を新区割りに合わせ整地」等、指図→実装の経緯そのもの。
   気づいたら `git reset --hard <旧tip>`（reflog に残っている）で戻してやり直す。
2. **`--path-glob` の `*` はスラッシュを跨ぐ**（Python の fnmatch。シェルの glob とは違う）。
   `Assets/Edo/Terrain/*.asset` は `Assets/Edo/Terrain/details/BroadleafTree.asset` **にも当たる**。
   意図がトップレベルだけなら `--path-regex '^Assets/Edo/Terrain/[^/]+\.asset$'` を使う。
   今回は details/ も落として構わなかったので、**落とした3本を後から復元**して決着させた
   （`.git/lfs/objects` に実体が残っていたので sha256 一致で戻せた）。

**書き換え後は必ず旧 HEAD と全ツリーを突き合わせる**（ファイル数と blob ハッシュ）:

```bash
git clone ~/edo-history-backup-YYYYMMDD.bundle /tmp/edo-old   # checkout は失敗してよい
cd /tmp/edo-old && git ls-tree -r <旧tip> | awk '{print $3" "$4}' | sort > /tmp/old.txt
cd - && git ls-tree -r main | awk '{print $3" "$4}' | sort > /tmp/new.txt
diff /tmp/old.txt /tmp/new.txt      # 何も出なければ作業ツリーの中身は完全同一
```

⚠ `git filter-repo` は安全策として **`origin` リモートを削除する**。あとで付け直す:

```bash
git remote add origin https://github.com/topi-topix/edo.git
```

最新版を入れ直す:

```bash
cp ~/edo-keep/Akasaka.unity Assets/Edo/Scenes/
cp ~/edo-keep/*.asset Assets/Edo/Terrain/
git add Assets/Edo/Scenes/Akasaka.unity Assets/Edo/Terrain/
git commit -m "chore: シーンと地形の最新版を入れ直す(LFS履歴の掃除)"
```

### Step 3 — 検算（push する前に必ず）

```bash
python3 docs/maintenance/measure_lfs.py     # 下の Step 6 参照。無ければ下記スクリプトを作る
```

期待値: **合計 0.3〜0.5 GB / パスごと1本**。ここが減っていなければ push しない。

`git log --oneline | wc -l` でコミット数が保たれていることも見る（指図の経緯が消えていないか）。

### Step 4 — GitHub 側（ユーザーの判断・操作）

**ここから先はユーザーの確認を取ってから。** 公開リポジトリを消すので、
star / fork / issue / Wiki が付いていないかを先に確認する。

- (a) リポジトリを削除して作り直す → `git push -u origin main` で入れ直す
- (b) サポートに purge を依頼して `git push --force origin main`

⚠ **`gh` の既定トークンには `delete_repo` スコープが無い**ので、(a) の削除は
`gh auth refresh -h github.com -s delete_repo` かブラウザでユーザー自身がやることになる。
再作成と push は `repo` スコープで足りる。

**「新しい方を先に作ってから旧を消す」順序は勧めない。** LFS クォータは**アカウント単位**なので、
超過中に別リポジトリへ push すると弾かれうる。同名も同時に作れず、リネームの手間が増える。
削除先行でも、バンドル＋`.git/lfs/objects` が揃っていれば復元できる（Step 0 の検証を通すこと）。

### Step 5 — ローカルの後始末

```bash
git lfs prune --dry-run --verbose   # ⚠ 必ず dry-run から。消す前に何が消えるか見る
du -sh .git .git/lfs
```

⚠ **`git lfs prune` はほとんど効かないし、効かせてはいけない。**
`archive/local-history-2026-08-02`（ローカルのみ・復元不可）と、書き換えていない
worktree ブランチ（`claude/*`）が旧履歴を保持しているため、それらの LFS 実体は retain される。
2026-08-15 の実測では **2864本中2662本が retain、消えるのは17 MB だけ**だった。
ローカルの `.git/lfs` が 18 GB のままなのは**正常**で、remote の使用量とは無関係。

### Step 6 — 検算スクリプト（`docs/maintenance/measure_lfs.py` として置いてある）

`main` の履歴が抱える LFS 実体をパス別に集計する。掃除の前後で走らせて比べる。

---

## 5. 終わったら

- メモリ `edo-github-repo` と `akasaka-scene-bloat` の数値を更新する
- **本命の A（シーン分割）に着手する。** これをやらないと約28セッションで元に戻る

---

## 6. 実施結果（2026-08-15）

| | 実施前 | 実施後 |
|---|---|---|
| LFS 実体（`main` の履歴） | 7.57 GB / 279本 | **0.54 GB / 174本** |
| うち `Akasaka.unity` | 6.46 GB / 55本 | 0.24 GB / **1本** |
| うち `Terrain` | 1.00 GB / 94本 | 0.17 GB / 34本 |
| コミット数（`main`） | 139 | 141（139保持 + 入れ直し1 + 復元1） |
| 作業ツリーの中身 | — | 676ファイル全部が blob ハッシュまで旧 HEAD と一致 |

- GitHub 側は **リポジトリを削除して同名で再作成**し、`git push -u origin main` で入れ直した
  （star / fork / issue いずれも 0、Wiki も空だったことを確認済み）。
- 新 `main` の tip は `d49a8b1`。LFS 174本 = 575 MB をアップロード。
- `archive/local-history-2026-08-02`（137コミット, `da65b5f`）は無傷。
- バックアップ `~/edo-history-backup-20260815.bundle`（112 MB, 全7ref, verify 済み）と
  `~/edo-keep/` は当面消さないこと。

**これは止血にすぎない。** シーンが 246 MB のままなので、
**約4コミットで再び 1 GiB を超え、約28セッションで 7 GB に戻る。** 次は A（シーン分割）。
