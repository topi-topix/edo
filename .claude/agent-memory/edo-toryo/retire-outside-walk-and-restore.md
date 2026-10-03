---
name: retire-outside-walk-and-restore
description: 区画が縮んだ邸で群を降りて区域外を退けると、子1つの入れ物を「駒」と読んで丸ごと消す。段の資産から写し戻すと葉のプレハブの繋がりが切れて生で焼かれる
metadata:
  type: project
---
2026-10-03 EDO-0535 松江松平(区画が縮み約1,513 m² が土井へ)。

1. **症状**: 植栽を幹の足(transform.position)で PIP して退けたら、「子が1つ以下=駒」の判定で
   入れ物10個(G_Tanikage・帯W3 法尻の草地 ほか 338 本)が原点 (0,0,0) で「区画外 1244m」と読まれ丸ごと消えた。
   **対処**: 駒の判定は LODGroup/Renderer が自身に在るか、子0 のときだけ。入れ物は位置を持たない。必ず dry で数えてから消す。
2. **症状**: 消した入れ物を段の資産(`Parts/<邸>__Niwa.prefab`)の子から `Object.Instantiate` で写し戻すと、
   場面では prefab 実体に見えるが、書き戻すと**自分の段の実体**扱いで生の GO として焼かれた(MF 1→274・5.16→5.28MB)。
   **対処**: HEAD の段を一時資産に置き、`Group()` で解いてから各駒を `PrefabUtility.ConvertToPrefabInstance(駒, 葉の元)` で繋ぎ直して
   もう一度書き戻す(PI 1482・GO 91・MF 1 = HEAD と同じ形)。⛔ 段ごと消して入れ直すのは許可の分類器が止める。
3. 継ぎ目に相手の run(`a`/`b`)が無い隅は Stage3 の腕の下の基壇が敷かれず、隅が 0.24〜1.00m 浮く ──
   Stage3 で `EdoBuild.KadoArm` の実測から敷くよう直した(Stage2→3→2 の順に流す)。

関連: [[stale-impl-after-parcel-redraw]] [[koba-writeback-ledger-empty]]
