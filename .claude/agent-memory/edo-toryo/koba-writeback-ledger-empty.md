---
name: koba-writeback-ledger-empty
description: 作業場で Stage を流しても「書き戻す(触った分だけ)」が台帳0件で何も書かないことがある。段別の邸は(選択中)で拾う
metadata:
  type: project
---

**症状**: 作業場(Koba)で Stage2〜6 を流して建て直したのに、`Edo/屋敷/プレハブへ書き戻す(触った分だけ)` が
**「書き戻す変更はありません」**。`Edo/屋敷/切り出し状況を検査` も「台帳=0 件 / ovr 0 / 構造 0」と出て、
段は全部「解けたまま」。放っておくと丸ごと失われる(Koba.unity は gitignore)。

**原因**: 台帳(`SessionState`)にルートが載るのは `EnsureRootEditable` が**その巡で解いたとき**だけ。
段別の入れ子プレハブの邸は本体がプレハブ実体のまま残り、解けるのは段なので、本体が台帳に載らない。

**対処**: 自邸だけを名指しで書く — `EdoYashikiPrefab.Convert(new List<string>{"<ルート名>"})`
(= `Edo/屋敷/プレハブへ書き戻す(選択中)`)。「段 書0/据置7」と出ても**段の .prefab は実際に書かれる**ので、
`git status` と資産を `LoadAssetAtPath` で読み直して中身を確かめること。⛔ (全部・強制)は押さない。
