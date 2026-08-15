# LFS 履歴の掃除（作業計画・引き継ぎ用）

作成 2026-08-15。**未実施**。この文書だけで別セッションが着手できるように書いてある。
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

現在のシーンと地形も退避しておく（書き換えで作業ツリーが reset されるため）:

```bash
mkdir -p ~/edo-keep && cp Assets/Edo/Scenes/Akasaka.unity Assets/Edo/Terrain/*.asset ~/edo-keep/
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
git filter-repo --force --refs main \
  --path Assets/Edo/Scenes/Akasaka.unity \
  --path-glob 'Assets/Edo/Terrain/*.asset' \
  --invert-paths
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

### Step 5 — ローカルの後始末

```bash
git lfs prune            # main から参照されなくなった LFS 実体を消す
du -sh .git .git/lfs     # archive ブランチ分（約7 GB）は残る。これは正常
```

### Step 6 — 検算スクリプト（`docs/maintenance/measure_lfs.py` として置いてある）

`main` の履歴が抱える LFS 実体をパス別に集計する。掃除の前後で走らせて比べる。

---

## 5. 終わったら

- メモリ `edo-github-repo` と `akasaka-scene-bloat` の数値を更新する
- **本命の A（シーン分割）に着手する。** これをやらないと約28セッションで元に戻る
