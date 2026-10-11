---
name: outside-target-reads-pregrade-road
description: 皮の解き(SkinHeightSolve)の区画の外の狙いが造成前の地盤(base_dem)の道を描き、均した道の上に線から 1:1 の土の棚 +1.8 を立てた(岡部 辺41 s45〜62・第109巡)
metadata:
  type: project
---

2026-10-11 EDO-0502 第109巡(岡部 Stage3b・台の前の溝 Mizo_Minami)。

**症状**: 道に面する溝の外(区画の外)に、線から 1:1 で下る土の棚(線の外 0.45 で道 +1.5・最大 +1.8)。溝の駒に「皮が天端に被る」1815 点。
OutsideBase(区画の外 = base_dem・道の均し・今の地形の min)を直しても、DesignOutsideOwn に min を足しても変わらなかった。
**原因**: SolveCtx.Target の区画の外の枝が OutsideOwnGround(…, design.baseAt) を返す。解きの間の design.baseAt は BaseDem()
(OutsideBase は DesignOutsideOwn の間だけ差し替えて戻す)── 造成前の三べ坂の道は 12.2〜12.5 で、Stage1 が均した道(10.5)より 2m 高い。
SkinSolveTrace で「Target 12.245・区画の内 False・地形 10.539・lo −∞」と出て分かった(SkinTrace の TrLog は解きでは出ない ── SkinSolveTrace を使う)。
**対処**: Target の区画の外を今の地形(probe)との min に(EdoBuildSkinSolve.cs SolveCtx.Target)。辺41 の線の外 0.45 は最大 +0.15・0.3 超え 0/192。
⚠ 低くした道の側で N39_1 の前の溝の笠(FrontMizoKasa 009〜012)の下の隙が 13→25 点(最大 0.49)に増えた ── 笠が線に接して、外の皮が下がった分だけ見える。

**How to apply:** 区画の外の土が「線から一定勾配で下る棚」なら、狙い(Target)がどの地盤を読んでいるかを SkinSolveTrace で先に見る。関連: [[michi-narashi-outside-parcel]] [[prev-grade-left-in-neighbor-after-parcel-move]]
