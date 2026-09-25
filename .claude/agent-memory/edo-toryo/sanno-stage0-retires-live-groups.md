---
name: sanno-stage0-retires-live-groups
description: 山王 Stage0_Retire は今の Keidai・Sando(名木 Meiboku 20 本を含む)を非活性の Kyu_z857 へ移す。建て直しは Stage1 から流す
metadata:
  type: project
---

症状(2026-09-25 EDO-0430): 「整地から建て直す」で Stage0→1 を流したら、Stage0 が **いま建っている** `Keidai`(門・社殿・
井戸・**名木 Meiboku 20 本**)と `Sando` を新しく作った非活性の `Kyu_z857` へ移した。Stage2〜9 は群を作り直すが、
Meiboku は Stage7 の受け持ちなので、そのまま書き戻すと名木が消える。

原因: Stage0 は z=857 の旧実装を退避する一回きりの手で、名前(Keidai/Sando)だけで拾う。冪等でない。
一括(BuildAll)も Stage0 から始まる。

対処: 建て直しは **Stage1 から**。踏んだら `Kyu_z857` の子を根へ戻し、空の `Kyu_z857` を消してから書き戻す
(プレハブに `Kyu_z857` は無いのが正)。関連 [[retired-stage-makes-fake-counts]]
