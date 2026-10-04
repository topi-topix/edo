---
name: redrawn-sashizu-shapes-and-stale-joints
description: 図から起こし直した指図は欄の形(poly/pts/place の文字列)が変わり、旧い隅の joints が残る。松江松平 EDO-0554 で踏んだ
metadata:
  type: project
---

松江松平の起こし直し(2026-10-04・EDO-0554)で踏んだ3つ。

1. **欄の形が変わる**: terraces/munes/service/gardens が `poly`、runs に `pts` だけの run(edge/s0 無し)、`place` が bool と文字列("置く"/"置かない…")の両方、`rails` が消える、石段に `pos` が無い。
   **Why:** 旧ビルダーは u0..v1・edge を無条件に読むので KeyNotFound。Stage2 は群を Clear した後に落ちて外周が空になる。
   **How to apply:** 読み替えは `NormalizeShapes`(D を読んだ直後)と `PolyOrRect` に寄せた。矩形で読む Stage は `PolyApprox` を ⚠ で刷る。他邸の起こし直しでも同じ形が来る。
2. **旧い隅の継ぎ目が残る**: 谷の境を木柵へ変えたのに joints に J_P3〜J_P12 の練塀の隅(kado)が残り、PlaceKado が谷底に隅を立てた(fences.hard「谷底に練塀を置かない」と矛盾)。
   **How to apply:** 両側の辺に塀・長屋の run が無い隅は据えない(PlaceKado)。指図方へ joints の掃除を差し戻す。
3. **DanPlan の段の上限は柔らかい(1.00)**: 指図が「段差 ≤1.3 硬い・1間で超える所は半間で刻む」と言うと、1間の区間しか切れず 1.40 の段が出た。
   **How to apply:** `EdoBuild.DanPlan(chain, out note, gates, stepQ, minSec, stepHardMax)` を足した(minSec = 半間)。崖の上の練塀 212m で段 27・最大 1.00。

4. **指図方が同じ時間に json を書き換える**(第2段 2026-10-04): Reload() の度に新しい json を読むので、Stage1 は Fukugen を段で均した後、Stage6 は Fukugen を外した json で座を測り、中仕切 NJ_Oku_S_W の座が 20.1(地形は 27.0)で 6.5m 食い違った。
   **How to apply:** 流す前に `git status docs/Sashizu/<邸>_sashizu.json` を見る。並行で書かれているなら、その欄に触れる Stage は書き終えてから Stage1 から流し直す。
5. **poly の棟は roof.parts の矩形へ割る**(`MunesExpanded`)・帯割り屋根の棟は外形の縦横を問わない(大棟の向きは部材が持つ)。傾いた四角の枠は `EdoBuild.QuadFrame`、線の端から決まった長さの石垣は `EdoBuild.SnapPieceToLine`(駒は基壇の割り付けで数を出し、伸縮は端数だけ ── 1駒を 1.55 倍に伸ばしかけた)。

6. **野面の網は一点に三本集まると継ぎを上書きする**(第3段): 天端 26.7 の二本と 26.2 の一本が同じ隅に集まり、出隅が継がれず 1.04m の口。PlaceNozuraNet に「天端の揃う相手を先に・継いだ端は上書きしない」を入れた。
7. **自前の 0.5m 刻みの走査は最後の標本を取り損ねる**: `for (sq=s0; sq<=s1; sq+=0.5)` は s1 が 0.5 の倍数でないと区間を閉じず、腰石垣 3 本を「1駒も続かない」と誤って落とした。標本数を数えて最後を s1 に。止めの地盤は描かれた地表でなく造成前の面で読む(線の外の格子が混ざって 0.1〜0.3 低い)。
8. **remap の menu は打たない**: 新しい FBX 26 本は、その本だけを AddRemap で結ぶ execute_code(錠のファイル付き)で 40 秒。

9. **長屋門の扉は土台の底の下へ垂れる**(gate-drop): SeatBottom が扉の下端を底と読み長屋が 2.3m 浮いた。受けの上に載る頂点だけで据える(EdoBuild.SeatOnBeds・札の局所0より下は数えない・受けの箱の縁 0.25 内)。受けはその run の基壇だけ(隣の高い基壇で S_Hei_P0 が 1.40 跳んだ)。
10. **隅長屋の手は焼いた向きと逆の隅がある**: 内角 106 の P23 で +X の腕が辺の延長へ出て 5.04m 区画の外。EdoBuild.ChooseHandInside で鏡と比べる。KadoDeg は外角(74)で返す ── 隅長屋の名は内角。
11. **普請検査の「区域侵犯・浮き」は一体の長屋の軒と基壇を読み違える**: 長屋の外面は足元2mで測ると −0.26(線の内)。塀の浮き 110 駒は石の天端を見ていなかった(実の浮きは斜面の run の 10 駒)。

関連: [[pitfall-writeback-mcp-timeout]](段ごとに 25〜40 秒・続けて投げた execute_code も詰まる)
