---
name: sukibei-t-end-bite-zero
description: 透塀の中門への突き付け(t の端)に ClipRunEndsToGates をそのまま使うと半厚 0.30 を食い込ませ、スパンが 1725mm になって全駒が「部材無し」になる
metadata:
  type: project
---

症状(2026-09-24 EDO-0430): Sukibei_E の t の端を中門の実メッシュへ取るため `ClipRunEndsToGates(pa,pb,H,halfT=0.30,…)` を通したら、
端が門の中へ 0.308m 入り、辺の等分が 1928→1725mm になって 14 駒すべて「1725_nn が無い」で建たなかった。
原因: `ClipRunEndsToGates` の `halfT` は `OpeningJambs` の**食い込み(bite)**。柵・板塀(門が傾いて据わる)の作法で、走りと同じ軸に据わる門へ突き付ける木口には要らない。
もう一つ: 返る端は**脇柱の角の点**(横へ 0.01m ずれる)なので、そのまま採ると走りが 0.06° 振れて隅の側で目違う。
対処: t の端は bite 0 で測り、端を元の seg の線へ射影して戻す(`EdoSannoShaRebuild.Sukibei`)。中門との隙 0.006/0.007 → −0.0005m、隅の取り合い −0.310(設計の重なり)は不変。
⚠ 透塀どうしの −0.090・隅との −0.310 は部材の設計の重なり(柱が節点をまたぐ・c の端を引く)で、欠陥ではない。

関連: [[run-end-at-opening]] [[gate-wall-closure-rule]]
