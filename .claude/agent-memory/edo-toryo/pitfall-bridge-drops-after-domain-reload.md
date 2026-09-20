---
name: pitfall-bridge-drops-after-domain-reload
description: After refresh_unity(compile), the MCP bridge reports "No Unity Editor instances found" for ~2min — poll the status file, don't conclude Unity is down
metadata:
  type: project
---

`refresh_unity(compile="request")` のあと、MCP が
`No Unity Editor instances found. Please ensure Unity is running with MCP for Unity bridge.`
を返すことがある。**Unity は落ちていない** — domain reload 中で listener が閉じているだけ。

- **症状**: `read_console` などが `Unity is reloading; please retry` → やがて
  `No Unity Editor instances found` に変わる。`wait_for_ready=true` でも返ってこない。
- **原因**: domain reload 中は port 6401 の listener が閉じ、python 側の instance 探索が空振りする。
  復帰まで当プロジェクトでは **約 2 分**(Assets/Edo だけで数百ファイル)。
- **対処**: プロセスと status ファイルで生死を見る。
  - `pgrep -fl "Unity.app/Contents/MacOS/Unity"`
  - `~/.unity-mcp/unity-mcp-status-1340bbd7.json` の `reloading` / `reason` / `last_heartbeat`
  - `lsof -nP -p <pid> | grep ":6401 (LISTEN)"` が立てば復帰。立った直後の 1 回はまだ
    空振りすることがあるので、もう一度だけ叩く。
  - コンパイル結果は bridge を待たずに `Logs/Editor.log` の `grep -E "error CS"` で読める
    (⛔ `~/Library/Logs/Unity/Editor.log` ではない — このプロジェクトは
    project-relative の `Logs/Editor.log` へ移している)。

## もう一つの原因: `~/.unity-mcp` に**別プロジェクトの古い port 登録**が残っている(2026-09-20)

**症状が違う** — Unity は idle・`reloading:false`・心拍が数秒前なのに、同じ呼び出しが
**一回おきに** `No Unity Editor instances found` を返す(成功と失敗が交互)。

- **原因**: Unity は起動時に 6400 が埋まっていると **6401 へ退避**する
  (`Logs/Editor.log` に `Port 6400 still occupied after 3s; falling back to port 6401`)。
  `~/.unity-mcp/` には `unity-mcp-port-<hash>.json` が**プロジェクトごとに**残り、
  当プロジェクトとは別の `/Users/toshio/project/unity-project/Edo/Assets`(2026-07 の登録)が
  6400 を名乗ったまま居る。探索がその古い行を引くと空振りする。
- **見分け**: `cat ~/.unity-mcp/unity-mcp-port-*.json` で `created_date` が何ヶ月も前の行があり、
  `unity-mcp-status-<hash>.json` の `unity_port` と食い違う。
- **対処**: ⛔ 再起動を頼まない・⛔ 待たない。**もう一度そのまま叩く**(交互なので次で通る)。
  タイムアウト側(`Timeout receiving Unity response`)は本当に Unity が重いので、
  こちらは `%CPU < 20` まで待つ。⛔ 二つを同じ扱いにしない。

**Why:** 「Unity が落ちた」と誤診して再起動を促すと、claim と未保存の作業を失う。
**How to apply:** bridge が無いと言われたら、まずプロセスと status ファイル、次に Editor.log。

関連: [[pitfall-writeback-mcp-timeout]] / [[pitfall-sanno-sukibei-kado]]
