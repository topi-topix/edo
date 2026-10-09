---
name: named-face-not-normal-to-line-sawtooth
description: 名指した見え面(NozuraSeg.face)が区間の線と直交しないと、野面の継ぎ目ごとに鋸の歯(前後 0.08〜0.42)と走りの口(0.05〜0.25)が出る ── 石段の脇の返しの天端の線は軸から 2〜9° 振れる
metadata:
  type: project
---

2026-10-09 EDO-0502 第64巡(岡部 K_Dan1/K_Dan2 の脇の返し TW_Kado_Shumen_Side0/1・TW_Higashi_Tsuyo_Side0/1・積み止め)。
施主「石垣の部材のつなぎ目で段差」。光線で継ぎ目の両脇の見え面を測ると、同じ区間の隣どうしで 0.08〜0.10、区間の境で 0.23〜0.42 の前後差、
走りの向きの射影で 0.05〜0.25 の口。

**原因**: 脇の返しは見え面を石段の芯へ名指す(軸の法線)が、天端の線(StairSideCrestLines)は見付が段ごとに 0.3 増え法 3分で 0.09 ずつ退くので
軸から 2〜9° 振れる。駒の yaw は名指しの向き・見え面の寄せは駒ごとに天端の前の縁を線へ ⇒ 駒ごとに線へ寄せ直して鋸の歯、走りへの射影の突き付けは
奥行 × sin(振れ) だけ長く読んで口。PlaceNozuraRun の log の「継ぎ目の隙の最悪」は走りの射影なので 0 と出て気づけない(末の隙 −0.75 が手掛かり)。

**直し**: EdoBuild.FaceAcross ── 名指しは「側」だけ採り、向きは区間の法線(PlaceNozuraRun の face/faceOn・PlaceNozuraNet の faceNear)。
口 4→(隅の誤対を除き)0 級・sideFace の見え面−端の線 0.45→0.25。

**How to apply:** 野面の継ぎ目の段差は光線で測る(EdoBuild.NozuraSeamReport・Stage3b の末)。⚠ 坂の run(袖)の前後差は「駒ごとに天端の最高の前の縁を線へ」
寄せる測りの残り(法 × 天端の差)で、隅の踊り場と勾配の駒の間(袖 049f × Kado52 0.36)は設計の天端の段差(21.0 の水平の後 1 駒で 18.99 の踊り場へ戻れない)。
関連: [[nozura-wall-traps]] [[stair-side-crest-lines]]
