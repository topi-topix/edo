---
name: bulk-delete-denied-by-auto-mode
description: 旧案の生成物を execute_code の DestroyImmediate で一括削除すると、施主の指示があっても auto mode の分類器が「取り返しのつかない破壊」で止める
metadata:
  type: project
---
症状: 2026-10-03 土井 EDO-0533「古い石垣などは削除」で、Edo_Yashiki_DoiOsumi の段7群(5334 transform)を EnsureEditable → DestroyImmediate する execute_code が分類器に拒否された。
原因: 依頼は呼び出し元(エージェント)経由で、施主本人の許可と見なされない。拒否は「同じ結果を別の手で」も禁じる(小分け・SetActive への言い換えも不可)。
対処: 一覧(段ごとの数・出どころ)まで済ませて止め、施主に許可の付与か、施主自身がメニュー/手で消すかを仰ぐ。段のプレハブは git にあり戻せる旨を添える。
