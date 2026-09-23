---
name: editor-dll-blocked-by-other-session
description: 別セッションが直している .cs が赤いと Editor アセンブリが焼けず、自分の C# の直しは何度 refresh しても反映されない
metadata:
  type: project
---

**症状**(2026-09-22・山王)。`refresh_unity` を投げても `Assembly-CSharp-Editor.dll` の mtime が
何分経っても動かない。Unity の %CPU は 2%(= 回っていない)。`Assembly-CSharp.dll` だけが新しい。

**原因**: `read_console(types=["error"])` に**自分が触っていないファイル**の CS0117 が 2 件
(別セッションが書きかけの `EdoGardenSurfacePaint.cs` が、まだ `EdoAssets` に無い呼び名を参照)。
赤い間は Editor アセンブリが出ないので、**自分の直しは一行も効かない**。
しかも相手は `EdoAssets.cs` を**こちらが claim している**ので足せず、待ち行列で止まっていた(相互待ち)。

**How to apply:**
- dll の mtime が動かず CPU も静かなら、**まず `read_console` の error を読む** — 自分のファイル名が
  無ければ待っても直らない。⛔ refresh を繰り返さない。
- 相手が自分の claim したファイルを要ることが多い ⇒ **Unity とファイルの claim を返す**のが最短。
  自分の据え付けとシーン・プレハブの保存だけ先に済ませ、コンパイルが要る直し(検査の結線など)は
  次の巡へ送る。報告に「どの .cs が赤くて誰が持っているか」を書く。
- `edo_session.py release` は待ち行列の先頭に 15 分の予約を出すだけ ── **相手への連絡は呼び出し元の仕事**。

関連: [[pitfall-bridge-drops-after-domain-reload]] / [[cs-edit-is-not-claim-free]]
