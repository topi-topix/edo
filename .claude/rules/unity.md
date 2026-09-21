---
paths:
  - "Assets/**"
  - "Tools/Blender/**"
---

# Unity / Blender を触るときの一線(CLAUDE.md「触ると壊れるもの」から移した・2026-09-13)

- **複数の Claude Code セッションが同時に動く。** 作業は `python3 Tools/Session/edo_session.py start <屋敷>`
  で始める(指図だけなら worktree、Unity なら `--unity`、Blender なら `--blender`。⛔ Blender は
  worktree では回せない)。⛔ **Unity は排他**。作業が切れたら即 `release --resources unity`(20分未使用は
  待っている側が自動で引き取る)。埋まっていれば `wait --resources unity`。返した側は次の人へ SendMessage。<!-- obl:unity-release canon -->
  ⛔ `git add -A` / `git commit -a` は門番が止める。→ `docs/session-coordination.md`
- **屋敷は1軒1プレハブ。** ビルダーの `Group()` が前に自動で解き、保存時に**この巡で触ったルートだけ**が
  書き戻る(2026-09-21・EDO-0282②。以前は保存のたびに 83 本を舐めて 74 本・128MB を書き直していた)。
  手で押すなら `Edo/屋敷/プレハブへ書き戻す(触った分だけ)`、`Group()` を通らない手直しは `…(選択中)`。
  ⛔ `…(全部・強制)` は**解けたままの他邸を巻き込む**ので救出のときだけ。
  ⚠ 台帳は `SessionState` なので**エディタを再起動すると消える** — 解けたまま離席しない。
  **Revert All を押さない。**
- **大きい邸は段(ルート直下の群)ごとの入れ子プレハブ。**(2026-09-21・EDO-0282③)
  松江松平 42.0MB・岡部 37.0MB・土井 15.1MB の3本は `Assets/Edo/Prefabs/Scene/Parts/<邸>__<段>.prefab`
  に分かれ、**触った段だけ**が書き直る(門だけ直した巡は 0.015MB)。内訳は `Edo/屋敷/切り出し状況を検査`。
  ⛔ **葉のプレハブまで解かない。** `Completely` で解くと木や部材の接続が切れ、次の書き戻しで
  同じ中身が生のオブジェクトとして直列化されて太る(庭が 5,155 個すべて生で 15.2MB を占めていた)。
  解くのは `EdoYashikiPrefab.Group()` / `EnsureEditable()` に任せる。→ `docs/maintenance/scene-size.md` §8
- **地形の編集は Undo の外。** 触る前に heightmap を `.bin` で退避。`TerrainData.asset` と `.unity` も。
- **2026-08-22 に地形を作り直した。** 屋敷を建てる前に必ず造成ステージを流し直す。→ `docs/terrain-georef-fix.md`
- **C# を直す間は作業場シーンで回す。** 赤坂を開いたままだと、1行直すたびに Unity が 83 プレハブを
  退避して復元するので待ちが 53 秒。作業場(`Edo/普請/作業場を開く`・一邸だけ)なら **9.8 秒**(実測
  2026-09-20・5.5倍)。屋敷の実体はプレハブ資産なので保存すれば赤坂は自動で追従する。
  ⛔ 取り合い・区域侵犯・検証レンダは作業場では見えない — 最後に `Edo/普請/赤坂へ戻す` で検める。
  → `Assets/Edo/Scripts/Editor/EdoKoba.cs` の冒頭
- **C# の誤りは Unity を起こさずに捕まえる。** `zsh Tools/Unity/cs_check.sh` が Editor アセンブリを
  Unity 同梱の Roslyn で通しで検める(3〜5秒・**Unity の claim が要らない**・他人の Unity を巻き込まない)。
  何も出なければ通る。⛔ 型の通りを見るだけで、据わり・取り合いは見ない — それは Unity で測る。
- **コンパイルが止まっていることがある。** `Library/ScriptAssemblies/Assembly-CSharp-Editor.dll` の mtime が
  ソースより古ければ実行しない。
- **⛔ 編集のたびに `refresh_unity` を投げない。** `create_script` / `script_apply_edits` / Edit は
  それ自体が取り込みと再コンパイルを起こす。重ねて投げると**もう一周ドメイン再読み込みが増える**
  (実測 39 回の要求のうち 7 回がこれ)。dll の mtime を見て待つ。投げてよいのは
  `edo_precheck_assembly.sh` が「古い」と言った**復旧のときだけ**。
- **MCP タイムアウト後の再送で多重実行が起きる。** 冪等でないステージ(特に造成)は実行済みかを先に確認。
  ガードのマーカーは active にする。
- **Blender の FBX を入れたらマテリアルを remap する**(`Edo/御殿/…マテリアルをremap`)。

