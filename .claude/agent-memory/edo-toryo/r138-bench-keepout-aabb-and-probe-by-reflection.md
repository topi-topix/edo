---
name: r138-bench-keepout-aabb-and-probe-by-reflection
description: 岡部 第138巡 ── 端の天端上げの背の小段を止めていたのは練塀の MeshRenderer.bounds の矩形の犬走り・小段の当たりは SodeBenches を reflection で呼んで点で刷れる(S2b を流さずに)・S1 の線の外の戻しの許し 0.3 が 0.26 の窪みを残した・型A と段落ちの帯を別々に書くと継ぎ目で交互になる
metadata:
  type: project
---
2026-10-15 EDO-0502 第138巡(普請方 r137/r137b の T1〜T5・K1・K2)。

1. **症状**: TW_Kita_Koshi の上げた端の返しの背に 0.54 の隙(普請方は「走りの外へ盛らない」と見立てた)。**原因**: endRaise の keepOut(犬走り)が
   練塀・隅の `MeshRenderer.bounds` を 2×inu 広げた**矩形**で、斜めの練塀の矩形が返しの背の 6m 四方を覆っていた(点で刷ると K だらけ)。
   **対処**: `EdoBuild.NearHulls(parts, d)`(実メッシュの凸包からの距離)へ。返しの腕の背は据えた後に `CrestFollowBackFill` で足した。
2. **小段の当たりは S2b(77 分)を流さずに測れる**: `SodeBenches` を reflection で `Invoke(null, new object[]{null})` ⇒ 各 BackBench を `BackBenchAt(k, p, cur)` で点ごとに刷る。
   ⚠ `_sideEndBenches`(延長の背の小段)は S2b の中でしか作られず、reload の後は空 ── そこだけは流さないと見えない。
3. **症状**: 角の桝の前の道に 0.26 の窪みが毎巡残る(pre=S1=S3d)。**原因**: S1 の `RestorePerimeterSpill_`(両向き)は許し 0.3 で、0.26 は戻さない。**対処**: 両向きは 0.02。
   S3d の最後にも駒の外形の下を除いて両向きで戻す(基壇の見え面の下を埋め戻さない ── 第114巡の禁)。
4. 南の練塀の内の溝は型A(FlushGroundToMizoTop)と段落ち(FlushGroundToStepTop)を別々に書いていた ⇒ 継ぎ目の節点は後に書いた方が勝ち、帯が交互になる。
   collect で候補を集めて `WriteBandCandidates` で一度に書く。
5. 返しの腕の背を CrestFollowBackFill で盛るとき、線を外形の最も前(法の足)に引くと見え面の法まで小段が被り、腕の見え面が土の歯で埋まった ⇒ 線は天端の帯(頂点の最高 −0.15)の前の縁。
6. 犬走りを実メッシュで測るようにしたら、#raise の noEndSpill(走りの外へ盛らない)が端の面で鉛直に切れ、腕の先に高さ 1.4 の土の切れ込みが見えた(F4 の擦り付けは駒の外形 +0.3 を触らない)── 普請方へ。
7. `EdoBuild.NearHulls` を邸の全部の駒(数千)で起こすと TopIndex の三角形化で 1 分を超え、MCP の送り直しで Unity が十数分ふさがった ⇒ 測る execute_code は近くの駒だけで・印を付ける。
**How to apply:** keepOut・犬走り・座の篩は bounds で書かれていないか先に grep。小段の謎の盛りは reflection で当たりを刷ってから直す。
関連 [[r137-sode-first-regex-and-partner-first]] [[r133-slope-crest-flat-chain-and-pad-into-ramp]] [[okabe-perimeter-rerun-order-and-neribei-measure]]
