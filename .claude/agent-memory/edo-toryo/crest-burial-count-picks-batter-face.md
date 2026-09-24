---
name: crest-burial-count-picks-batter-face
description: TuckUnderCrest の「天端より地表が高い点」は城の石垣の法(面)の下部も拾い 3.9〜4.1m の偽の埋没を出す。見え面を渡して天端の帯だけ数える
metadata:
  type: project
---

症状(2026-09-24 EDO-0430 山王 Stage3): 見える天端の帯で数えるようにした直後も「埋没 459 点・最大 4.13m」(TW_Zentei_W_006f ほか)。
原因: 平面の各点で「最も高い三角形」を天端とみなすので、法のある駒(CastleWall・見え面 +X)の法尻側は**法の面**が天端として拾われ、
根入れ(法の下部が地中)がそのまま埋没に数わる。
対処: `EdoBuild.TuckUnderCrest(..., faces:)` に駒ごとの見え面を渡す。見え面の向きの列で天端の最高 − 0.10 より低い点は法(`faceIn`)、
覆われた天端の点は見え面へ歩いて天端が地表から出る点に会えば帯の奥(`hidden`)。残りだけ埋没 → 459/4.13m が 298/0.90m に。
残った物は run の端の駒が横(走りの向き)から斜面に入る型(EDO-0425 と同じ)。

関連: [[dig-to-unbury-cascades]] [[base-and-wall-share-one-dependent-value]]
