---
name: side-bench-spill-and-fence-on-paper-gap
description: 石段の脇の返しの背の小段(sideBack)の端の法が本線の見え面の前へ土の箱を立てた・天端の垣が紙の口で空けられ石段の足元に切れ端が据わった
metadata:
  type: project
---

2026-10-09 EDO-0502 第62巡(岡部 K_Dan1 の両脇・施主写真12枚「全部気になります」)。

1. 足元の「平らな肌の大きな石」と石段の端の「斜めの土の面」は駒でなく**皮(EdgeSkin)**。光線で拾うと全部 EdgeSkin_Okabe。
   原因: `StairSideAndEndBacks` の sideBack の小段は keepOut が道の路盤だけで、返しの低い端の先の法(1:1.5・盛り上限 1.5 で頭打ち 18.0)が
   本線 TW_Kado_Shumen の見え面の前(門の内 16.50)へ回り込んだ。本線は小段を持たないので、既存の InFrontOfFace の篩(小段の線どうし)に入らない。
   さらに 2b が地形の節点へ 18.0 を書き、皮の縁の点が地形に留められて石段の端の脇にも斜めの土が出た。
   ⇒ 本線の最も近い区間の低い側(DesignY で測る)を篩う。地形の盛り残りは S1 から流して消す。
2. 天端の垣の切れ端(sx 0.18〜0.71)が石段の足元 16.9 に据わっていた: `PlaceDanKaki` が欄の紙の口 [4.56,10.37] で空け、解いた口 [3.13,12.83] との差に垣が残った。
   ⇒ Stage2b が解いた口を gapOf で渡す。
3. 角の天端の段(21.0 → 20.42)は袖の坂 TW_Kado_Sode の上端が背の法+0.15 で 20.54 止まり(2b の ⚠「上端 21.0 に届かない」)。設計の話。

**How to apply:** 皮に土の箱が出たら、先に SodeBenches の各 BackBenchAt をその点で刷る(反射で呼べる)。小段の篩は「小段の線どうし」だけでなく、
小段を持たない本線の見え面も要る。天端の垣・口に関わる物は紙の口でなく解いた口を読む。
関連: [[bench-end-slope-spills-and-3b-opposite-wall]] [[backbench-residue-cleared-by-stage1]]
