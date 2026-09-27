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
