---
name: worktree-codeonly-base-and-cs-check
description: Unity を使わない worktree の巡では、枝が古いコミットから切られていて指図の欄が無いことがある・cs_check は Library が無く空振りする
metadata:
  type: project
---

Unity を握らず worktree で C# だけ書く巡(2026-10-17 EDO-0502)で踏んだ二つ。

1. **worktree の枝が main より 164 コミット古かった** — 頼まれた指図の欄(const.nagayaKata・ishigakiScale)が json に無い。
   `git merge-base --is-ancestor <指図のコミット> HEAD` で確かめ、枝に自分の作業が無ければ `git merge --ff-only main`
   (⛔ `reset --hard` は門番が止める)。
2. **`zsh Tools/Unity/cs_check.sh` が worktree では黙って何もしない** — `Library/ScriptAssemblies` が worktree に無く、
   zsh の glob が「no matches」で落ちる(出力が空なので「通った」と誤読しやすい)。scratchpad へ写し、
   `$P/Library` を本体の `/Users/toshio/project/edo-unity/Library` に置き換え、`EDO_ROOT=<worktree>` を付けて走らせる。
   ⚠ 一つの Bash に `cd && G=$(...) && ...` と git を混ぜると worktree の門番が止める ── 一手ずつ打つ。

**Why:** 古い枝のままだと欄の無い json を読んで「指図に無い」と誤って差し戻す。空の出力を合格と読むと型の誤りを本体へ持ち込む。
**How to apply:** worktree で始めたら最初に HEAD と main の差を見る。cs_check は一度わざと誤りを入れて鳴るのを見るか、上の写しで走らせる。
