---
name: batter-cut-parts-measure-and-check
description: 法で切った段石・袖(DanKiri/SodeNori)へ差し替えると突き合わせの「幅」が赤くなる(ObbFootprint は縮尺を見ない)・袖の側面の目地が光線で 0.015〜0.02 の偽の口に出る・女坂の足は斜めに交わり切る形が無い
metadata:
  type: project
---

2026-09-26 EDO-0430(`EdoBuild.CutStairEndsToBatter`・山王 参道の階)。

- 症状: 差し替えた後、`EdoSannoSashizuCheck` が「参道の階 の幅が違う 5.51/5.26」。原因: 幅は中の段石の
  `EdoBuild.ObbFootprint`(駒の局所で測る ⇒ **縮尺を見ない**)。前の巡の突き付け(縮尺 0.943)は見えていなかっただけで、
  切った駒は形そのものが狭い(返しが法で段へ食い込む = 裁定B の姿)。対処: 検査側が「返しに当たらない段」か最上段で測る
  (直していない・検査の器は他窓が編集中だった)。
- 症状: 跨ぐ段(段1)の袖の側で口 0.014〜0.019 が斜めの一列に出る。原因: 袖の内の側面の**目地の溝**を光線が拾う
  (袖を 0.054 上げた側だけ帯に入る)。据えの口ではない。対処: 数えるなら目地の列を外す/高さを散らして中央値。
- 女坂の段0・段1 の端は前庭の南西の土留め(Castle Wall・鉛直)に約43°で斜めに交わる(離れの幅 0.27〜0.47)。
  法に平行な切りの駒では納まらない ⇒ 差し戻し(部材か納めの判断)。
- 焼き直しは 1 行だけの一覧を scratchpad に作って `dan_kiri_list` に渡す(焼けている行を焼き直すと FBX が差分になる)。
  新しい FBX は Refresh の後、埋め込みの材のままなので `Edo/山王社/新造部材のマテリアルをremap` をもう一度。

関連 [[short-return-tie-and-sode-extent]] [[nozura-wall-traps]] [[new-fbx-without-meta-reads-as-unbaked]]
