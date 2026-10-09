---
name: brute-force-measure-hangs-unity
description: 総当たりの計測を execute_code で打つと Unity の主スレッドが1時間以上ふさがり、MCP も compile_wait も全部タイムアウトする(2026-09-27 山王 前庭の窪み)
metadata:
  type: project
---

2026-09-27 EDO-0437: 前庭の窪みを測る `kubomi.cs`(点ごとに範囲内の全三角形を総当たり・0.05m 刻み)を 14:01 に送ったら、
Unity が CPU 90% のまま 15:05 を過ぎても戻らず、`MCP-FOR-UNITY: Command TCS timed out (N consecutive)` が 100 回超積まれた。
次の巡の棟梁は compile_wait も read_console も通らず着手できなかった(先の棟梁は compile_wait の重ね打ちで 50 分溶かし施主に止められた)。

**Why:** 30 秒を超える execute_code は MCP が再送する([[akasaka-open-resent-six-times]])ので、重い計測は重さ×最大6回。
sample(`sample <pid>`)の主スレッドは EditorApplication.update → 管理コードの深い呼び出しで、モーダル(CPU 0%)ではない。

**How to apply:** 計測は必ず升の索引(0.5m の hash)で三角形を引く(kubomi2.cs の形)+ 印のファイルで再送を弾く
([[long-run-guard-and-soft-only-converge]])。着手前に `tail Logs/Editor.log` で `TCS timed out` が積まれていないか見る。
積まれていて CPU 90% なら、前の計測が回っている ── 待つか Unity を落とすかは呼び出し元へ返す(自分で kill しない)。

**三度目 2026-10-05 EDO-0502 第18巡**: 隅の駒の腕に沿う面の出を `EdoBuild.RayToBodies` で 1,656 本(腕2×23点×18段×2隅)打ったら、
Unity が約 6 分ふさがり再送で TCS timed out 37 回・bridge が一度「instances なし」。その間に claim が他窓へ移り、書き戻し後の保存とレンダの撮り直しが出来なくなった。
⇒ RayToBodies は呼ぶたびに駒の頂点を舐める。**光線は 1 呼び出し 100 本まで**・印のファイル必須。楔は Stage のログ(継ぎ目の隙)と一枚のレンダで足りる。

**四度目 2026-10-05 EDO-0502 第19巡**: 隅の駒の頂点を材ごとに測る execute_code で、内側の輪の中に `mesh.vertices[i]` を書いた
(呼ぶたびに配列を丸ごと複写 → 頂点数² の大きな確保)。`sample <pid>` の主スレッドは `GC_alloc_large → GC_collect_a_little → GC_mark_some`
で、一回の確保ごとに全ヒープを舐めていた。30 分戻らず、作業に一度も入れなかった。
⇒ **`var vs = mesh.vertices;` は輪の外で一度だけ**(`sharedMesh.vertices`・`GetTriangles` も同じ)。送る前に輪の中のプロパティ呼びを目で検める。

**五度目 2026-10-09 EDO-0502 第63巡**: 野面の帯の検めを execute_code で `RayToBodies` 3.8 万回(駒 210 面 × 帯 × 奥行)にした ──
RayToBodies は呼ぶたびに mesh.vertices を複写して全三角形を舐める。10 分超 Unity を塞いだ。
⇒ 石の上面は **TopIndex(EdoBuild の中・NozuraCrestCover.Measure)で一度だけ索引を作って引く**。execute_code に RayToBodies の輪を書かない。
