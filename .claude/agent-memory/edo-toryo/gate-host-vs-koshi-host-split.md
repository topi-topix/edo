---
name: gate-host-vs-koshi-host-split
description: 表門を移す巡の罠 ── 腰石垣・門の内の下水の棟を gate.host で取ると表門の移動で一緒に動く ── roadEdge の文の「<棟> の前」で取り、口の無い棟は ps を NaN・拠り所(Mid)で向きを取る
metadata:
  type: project
---
2026-10-10 EDO-0502 第101巡(岡部 表門 辺39→辺40)で直した型。

- `RoadEdgePlan.Mid` = 口があれば口の芯、無ければ `anchor`(同じ辺の隣と接しない側の端)。`0.5f*(ps0+ps1)` を書かない(口が無いと NaN)。
- 棟は `RoadEdgeHost(roadEdge の文)` ── 指図が「N39_0 の前の野面の腰石垣」と名指す最初の run。無ければ gate.host。
- 口が無い棟: `hasGate=false`・ps0/ps1=NaN(比較が全部偽になり口の縁の処理が黙って外れる)・踏み段は置かない・踏面の文は要らない。
- OmoteGesuiPlan は門の口の脇で入口 J を測る型 ── 口の無い棟では測れず ★(「置き場は今のまま」は位置 s が指図に無い)。背の雨落ちは別の辺の門の s を引かない。

- 同じ巡で踏んだ3つ: ① GateInNagaya(口の版へ差し替え)が FrontForGutter(前の面の寄せ)の**後**だと差し替えが寄せを捨て、溝の外の壁が線の外 0.191 ⇒ 差し替え→寄せの順へ。
  ② 腰石垣の端の納め(妻の線の隅の駒 10-10j/k)が `if (r.h10)` の内にあり、欄の書き換えで「追記 2026-10-10h」が消えて**黙って打ち切り**に落ちた(隙 2.8・法尻 0.71)。
  ③ 10-10m の前の溝を「文に棟の名が出る」で拾い、別の溝 D_N40_Mae の棟 N40_0 にも 0.4m 据えた ⇒「<棟> の前の全長」で選ぶ。

How to apply: 門・棟の欄が動く巡は `grep -n 'Get(D, "gate")'` で host を「門のある棟」以外の意味で読む所を先に洗う。関連: [[gate-move-parts-bake-and-host-coupling]]
