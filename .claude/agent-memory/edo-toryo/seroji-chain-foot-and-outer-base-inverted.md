---
name: seroji-chain-foot-and-outer-base-inverted
description: 野面の鎖は最初の区間の footAt で全区間の見付を取っていた(石段の脇の返しと継いだ本線が段石の踏面を足元と読み底が 1〜1.5 浮く)・外周の基壇 IG_* は全辺で法の面が内向き(2026-10-11 EDO-0502 第106巡)
metadata:
  type: project
---
- 症状1: TW_Higashi_Se(背の路地の奥の石垣)を初めて建てたら、本線の駒の底が 14.0/13.7/13.4 で止まり路地の床 12.4 との間に 1.0〜1.5 の口。
  原因: `PlaceNozuraNet` が鎖(一直線・出隅で継いだ区間)の footAt を**鎖の最初の区間の物**で全区間に使う。鎖の頭が K_Tsuyo の脇の返し
  (StairGaps の footAt = 段石の踏面の列)だったので、本線の足元も踏面を読んだ。
  対処: 区間ごとに footAt が違う鎖は、点に最も近い区間の footAt で測る(EdoBuildNozura.cs の鎖の組み立て)。一つしか無い鎖は従前どおり。
- 症状2: 三べ坂の足元の土の盛り。原因: `PlaceIshigaki` は Castle Wall の局所 +X(鉛直な背)を外へ据えるので、外周の基壇 565 駒は全辺で
  法の面が屋敷の内を向く。const.kidan は「法肩を区画線に・基部は線の外へ h/4」で、そのまま翻すと根石が区画の外へ出る(区域 許容0)── 設計の話。
- 罠3: 背の路地のような「長屋の背から測る線」は算出物(python)では解けない(line=null・unresolved)。C# で実メッシュから解いて欄を組み直し、
  Stage2b の下の据えへ流す(SeRojiPlanOf)。皮の面は 0.5m ごとの平らな矩形(縦断の勾配を段で近似)── 1/20 でも 0.025 の段。

**How to apply:** 足元の違う区間を継ぐ鎖で見付が足りない駒が出たら、まず鎖の頭の区間の footAt を疑う。外周の基壇を触る前に裁定(法肩と区域)を取る。
[[castlewall-face-is-local-minus-x]] [[wallface-thin-axis-fails-on-deep-nozura]]
