---
name: prefab-yaml-has-guids-not-names
description: 書き戻したプレハブを grep して部材名・オブジェクト名が出ないのは正常。参照は GUID で、名は据え付けの中に出ない
metadata:
  type: project
---

**症状**(2026-09-22)。書き戻し後に `Edo_Sanno_Sha.prefab` を grep したら `薬師堂`・`Sanno_Do_` が
0 件で「書き戻しが効いていない」と誤診しかけた。`[EdoWriteBack] wrote=1 本体5.60MB` は出ていた。

**原因**: プレハブの YAML は**資産を GUID で**参照する(綴りは出ない)し、プレハブインスタンスの子の名も
そのままの行では出ない。⇒ **ファイルの grep は書き戻しの検めにならない。**

**How to apply:** 検めるのは二つだけ。
① `AssetDatabase.LoadAssetAtPath<GameObject>(<プレハブ>)` を開いて `transform.Find("<群>")` の
   `childCount` と子の名を数える(= 資産の中身そのもの)。
② どうしてもファイルで見たいなら `<部材>.fbx.meta` の `guid:` を引いて、その GUID の**出現数**を数える。

関連: [[pitfall-writeback-mcp-timeout]] / [[koba-writeback-ledger-empty]]
