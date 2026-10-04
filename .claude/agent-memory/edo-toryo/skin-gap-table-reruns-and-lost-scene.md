---
name: skin-gap-table-reruns-and-lost-scene
description: SkinGapTable を execute_code で呼ぶと約78秒×6回 Unity をふさぐ・その間に claim が他窓へ移ると、後の計測は別邸の作業場で黙って空振る(colliders 0・Find が nf)
metadata:
  type: project
---

2026-10-04 EDO-0502 第13巡(岡部)。端の口の内訳を取るため Stage3b と同じ部材の集めで `EdoBuild.SkinGapTable` を execute_code から呼んだ。
1回 約78秒 ⇒ MCP の時間切れで6回走り、Unity を約8分ふさいだ(結果のファイルは1回目で出ていた)。その後、呼び出しの間が空いて
unity の claim が土井の窓(EDO-0533)へ移り、作業場が土井に替わっていた。続けて打った見通しの光線の計測は
「一時の MeshCollider 0 個」「GameObject.Find が nf」のまま **成功で返った**(岡部の駒が無いのに全点「見える」と出た)。

**How to apply:**
- 重い表(SkinGapTable・CutEdgeSkin の報告)は Stage3b のログから読む。計測で呼び直すなら駒を名指して数を絞る。
- 計測の頭で必ず `GameObject.Find(GN)` の有無と作業場の名を返させ、無ければ止める(空振りを成功と読まない)。
- 呼び出しの間を 15 分空けない ── 6回の再送の待ちも空きに数えられる。
関連: [[akasaka-open-resent-six-times]] [[brute-force-measure-hangs-unity]] [[koba-left-dirty-by-other-window]]
