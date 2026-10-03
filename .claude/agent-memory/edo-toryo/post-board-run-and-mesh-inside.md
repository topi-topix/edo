---
name: post-board-run-and-mesh-inside
description: MidSection は世界座標を返す(TransformPoint を重ねると板が 438m 飛んだ)・内外の判定は MeshInside(MeshCollider+光線)で 0.15 秒 ── 総当たりは 25 分ふさいだ(二度目)
metadata:
  type: project
---

2026-09-26 EDO-0437 第7巡(山王 前庭の南の板塀 Ita_ZSE・隅の腕)。

1. **`EdoBuild.MidSection` は世界座標を返す**(root.TransformPoint 済み・名は「局所」に見える)。PostBoardRun で
   `transform.TransformPoint(l)` を重ねたら、柱は相殺されて正しい所に建ち、板だけ走りへ 438m 飛んだ。柱の台の篩いも
   全頂点を拾い、台の底 = 継ぎ足しの足と読んで台が 0.29 浮いた。**How to apply:** MidSection の点はそのまま射影する。
2. **重い内外の判定は `EdoBuild.MeshInside`**(駒を世界座標の一時 MeshCollider・層 31 に焼き、8 方向の光線を反復で数える)。
   野面の隅×袖 4 対で 148ms。execute_code で三角形の総当たり(頂点×8向き×全三角形)を書いたら 30 秒を超えて 6 回走り
   Unity が約 25 分ふさがった ── [[akasaka-open-resent-six-times]] に既に書いてあったのに読まずに踏んだ。
3. 野面の打ち切りの駒の隙 2 件・天端の被り 4 件は、部材方の野面の焼き直し(c027d97e・天端の石が内向きに焼けていた)の後に
   流し直すと 0 になった。皮の側に足した縁の閉じ(CloseRimAtHull)は今回 0 点で、まだ一度も効いていない(未検証の器)。
4. 回廊の出隅 E×S × 女坂の北の袖 039f は本物(隅の法の足の外角が袖へ約 0.19・y 25.0〜26.0)。帯の近似(控え〜見え面)でなく
   8 方向でも中と出る。

関連: [[parity-inside-test-false-intrusion]] [[kado-short-arm-and-foot-groove]] [[panel-on-crest-and-shoulder-traps]]
