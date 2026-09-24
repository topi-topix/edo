---
name: contact-cell-too-fine-on-sparse-meshes
description: EdoBuild.Contact を cell 0.1m で低頂点の駒(段石・袖 400〜700頂点)に使うと「測れず」と偽の隙が出る。0.25m(既定)で測る
metadata:
  type: project
---

症状: 山王の石段の袖(EDO-0415)で PlaceIshidanSode の検めが 30 駒に「小口との隙 測れず / 0.015m」を出した。
原因: Contact の筋を 0.1m にすると、疎な実メッシュでは両方の頂点が同じ筋に入らず NaN、または小口の面取り(深さ2cm)の頂点だけ拾って偽の隙。極値で測ると全駒 0.000m。
対処: 筋は既定の 0.25m で測る(EdoBuildIshidan.cs を直した)。疎な駒で細かい筋を使うなら、先に極値の差と面の平らさ(2cm帯の散らばり)で裏を取る。

関連: 女坂の曲がり(段石の yaw 差 2.5〜4.4°)10 か所で袖の走りに外側 0.14〜0.25m の口・内側 0.29m までの重なりが残る — 段ごとに段石の芯で回すので、幅の半分 × sin(曲がり) だけ袖がずれる。留めの駒が要る話で、据え方の直しでは消えない。[[measure-dont-nudge]]
