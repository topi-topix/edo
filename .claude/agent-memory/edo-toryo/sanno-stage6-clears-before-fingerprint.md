---
name: sanno-stage6-clears-before-fingerprint
description: 山王 Stage6 は群を Clear してから算出物の指紋を検めるので、指紋違いで落ちるとシーンの社殿が空になる。並行セッションが指図を書いている間は指紋が揺れる
metadata:
  type: project
---

**症状**(2026-09-23 EDO-0395): `EdoSannoShaRebuild.Stage6_Shaden()` が「算出物がいまの指図から焼かれていない」で例外。
その時点で `Keidai/Shaden` は既に空(Clear 済み・未保存)。指紋は 14:18→14:21→14:22 と3度変わった。

**原因**: Clear(grp) の後のループで初めて `Impl`(W())を引き、そこで指紋を検める。指図 json は他セッション
(社叢の EDO-0401)が planting を書いては bake している最中で、munes の欄と無関係でも全ファイルの指紋がずれる。

**対処**: ⛔ 自分で `bake_impl.py --write` しない(planting は他人の欄)。`python3 Tools/Sashizu/bake_impl.py sanno`
を 15 秒おきに回して「食い違い 0 件」になった瞬間に キャッシュを捨てる → Stage6 を流す。空になった群は保存前なら
流し直しで戻る。流す前に Stage6 の前で `Impl` を一度引いておけば空にならない(器の直しは未着手)。

関連: [[bake-impl-carried-src]]
