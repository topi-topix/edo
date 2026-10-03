---
name: kado-arm-overruns-short-edge
description: 区画の辺が隅の腕(±4.1m)より短いと、留め継ぎ隅が隣の辺を越えて区画の外へ出る・間の練塀は負の長さで据わらない。ClosureQA は 0 のまま
metadata:
  type: project
---

2026-10-03 EDO-0502 岡部(42頂点)。隅部材を焼いて 37 基据わったが、辺1〜3(2.1〜3.3m)に挟まれた Kado_P2/P3/P4 の躯体が
区画外 0.70〜1.28m(腰 1.2m 以下の頂点で測った)。短辺の練塀 10 run は「腕の実端面で挟むと長さが負」で据えない。
ClosureQA・OpeningQA・ParcelQA はどれも 0 で、この越えを見ない ── **Kakoi の駒の実頂点を区画へ PIP して距離を測る**しかない
(屋根・軒の 0.1〜0.19m は軒の越え=許容。躯体は最低点+1.2m 以下の頂点で見る)。
解くのは腕の短い隅(部材)か、短辺を一本の隅でまたぐ納め(設計)。棟梁は決めずに差し戻す。
⭕ 同日 a6e59f17 の腕の短い隅(EdoBuild.KadoArms)で P1〜P4 の躯体の区画外は 0 に、辺1〜3 の腕は 0.004〜0.14m 重なって素通し 0。
関連: [[run-end-at-opening]] [[stale-impl-after-parcel-redraw]]
