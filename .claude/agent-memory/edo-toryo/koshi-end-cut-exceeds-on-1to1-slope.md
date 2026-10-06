---
name: koshi-end-cut-exceeds-on-1to1-slope
description: 岡部の腰の土留めの端の背を小段+法1:1.5で切る koshiEnd は、背の法が設計の切土 1:1.0 なので切りが 1.3〜2.5m になり上限 1.0 で全部退く・坂の石段の a/b は従属値で上書きに追従しない
metadata:
  type: project
---
2026-10-06 EDO-0502 第31巡。

1. koshiEnd(nozuraEndRule 追記)を `EdoBuild.CutKoshiBench` で入れた。背の法は const.batterCut 1.0(1:1)なので、1:1.5 の法は今の法と交わらず
   切りは小段の縁から 2〜3m の所で最大 1.3〜2.5m(小段の帯の中だけでも 0.85〜1.58)── 上限 1.0 で 5 端とも退いた。
   残り 3 端は端の先の見え面の線上の地盤が天端より 0.27〜1.47 高い(普請方へ)。**型では解けない ── 法の勾配か切りの上限(設計)の話**。
2. 見切り石の埋没は「控えの奥の一点の背−天端」では捕まらない(TW_Kita_Koshi_3_0 は −0.49 でも石の背で 0.20 埋まる)。切るのは見切り石が退いた時だけ。
3. 坂の上の石段の `a/b` は `atS ± planeLen/2` の従属値で、上書きしても古い a/b が残り 8 段が 1.8m に詰まる。C# `KaidanAB` と python `kaidan_ab_on_route` が atS から解く。

**How to apply:** 端の納めの設計値が変わったら、まず各端の切りの最大と位置を刷って(CutKoshiBench の note)普請方へ渡す。
関連: [[nozura-end-rule-blocked-by-back-soil]] [[stair-position-is-terrain-dependent]]
