---
name: nozura-round3-measure-traps
description: EDO-0437 第3巡で踏んだ4つ ── 最も離れる向きの ContactPts は段石×隅の駒の 0.17 を見落とす・外形の中の「面の無い点」で皮が地形のまま溝・野面の入隅の法切り駒の見付は足元の面で取る・cs_check が他人の Starter Assets で倒れる
metadata:
  type: project
---

2026-09-26 EDO-0437 第3巡(山王 前庭の縁・参道の階)。

1. **「候補の向きのうち最も離れる向き」で測る ContactPts(scratchpad meas2)は、段石の端 × 野面の隅の駒のめり込みを見落とす。**
   参道の階 段1〜3 の端に隅の駒 kado2 の法の足が 0.06〜0.20 入っていたのに meas2 は段2 の −0.086 しか出さなかった。
   段石の端は**光線**(端の外面 RayFarthest → 相手 RayToBodies・当たった点が設計面 + 0.02 より上だけ)で測る。
   症状: 野面の相手へ段石の端が「割れる(mixed)」 → 原因: 石の出入り ±0.07 → 対処: `EdoBuild.EnvelopeCut`(見える当たりの包絡)。
2. **縁の皮は、駒の外接の外形の中でも駒の面が上下に無い点(凹んだ駒の縁)を「外形の中 = 上げない」扱いで地形のまま残す。**
   前庭 SE の背で 2m 格子の地形 15.7 が残り、駒の底 16.50 の下が 0.54 覗いた(裏込めの話ではなかった)。
   CutEdgeSkin に「背の土を駒の底まで」(近くの駒の底 ≦ 周り 0.6m の外の地盤 + BACK_FILL 0.35)を足して 0。
3. **入隅の可動側の法切りの駒の見付は足元の面(foot.terrace)で取る。** 部材方は W の南を見付 0.4 と読み H0600 を焼いたが、
   天端 16.11 − 面 14.50 = 1.61 で床が 1m 浮く ⇒ H1800 を焼き足した(sanno_nozura_nori_set.txt)。反対の端の見切り石は
   天端より下で前へ出るので、長さは天端の残りでなく**据えて両側を測って**短い方へ(0.65 は −0.04 入り、0.60 で 0/0.021)。
4. **`compile_wait.py` / `cs_check.sh` は未追跡の `Assets/Starter Assets/`(名に空白)で CS2001 を出して止まる**(他人の import)。
   その間は refresh_unity を1回 → `stat` で dll の日付を1回見る(sleep の見張りは門番が止める)。

**How to apply:** 野面の相手の取り合いを直したら、合否は meas2 でなく光線(段石の端)と RestGap(載る物)でも測る。
関連: [[oblique-contact-and-batter-wedge]] [[nozura-net-face-crest-end]] [[batter-cut-parts-measure-and-check]]
