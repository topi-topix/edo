---
name: slope-sode-flat-kado-and-end-specs
description: 坂の袖を区間ごとの背で測ると出隅で天端が飛ぶ・区間の継ぎ目が段の境に化ける・平らな斜交の隅の駒は坂で背と 0.5 離れる・名指しの端の型は EndSpec で渡す
metadata:
  type: project
---
2026-10-07 EDO-0502 第41巡(岡部 TW_Kado_Sode.sodeSlope・端の型)。

1. **坂の天端を「区間ごとの背の向き × 設計面」で引くと、出隅の節点で背の点が飛び天端が 0.43 落ちる**(勾配の寄せ 0.39 外れ)。
   ⇒ 0.1m おきの生の値を PAV(隣接の違反を均す回帰)で単調にしてから渡す(SodeSlopeSegs)。
2. **天端が坂の区間を鎖に継ぐと、継ぎ目ごとに「段の境」の駒(G−220)が立つ**(1m で 0.05 超の差を段と読む)。NozuraSeg.flow = true で止める。
3. **斜交の出隅の隅の駒(Kado52_H4800)は天端が平ら** ⇒ 勾配 0.35 の坂の上では腕の先で天端と背の差が 0.53 になる(硬 ≤0.3 を割る)。
   置き方では解けない ── 坂の隅の駒(部材)か線の折れの扱い(指図)。
4. 名指しの端(returnEnd・endKado・kadoReturnUniform)は EdoBuild.EndSpec に欄の文の値を入れて NozuraEndRule.spec で渡す。
   「延ばす向き 1.5m の内の実面」は平行に走る外周の石垣を拾う(距離 0.00)⇒ RunAxis で 30° 以内を除く。
5. 急な勾配(|g| ≥ 0.2)を低い見付で引くと ±0.12 へ寄る(±0.275/±0.45 は H0600 以上だけ)⇒ EdoAssets.Own.SannoNozura が一つ上の見付へ上げる。

関連: [[stepjoint-and-kado-return-traps]] [[nozura-end-rule-blocked-by-back-soil]] [[double-fold-kado-one-piece]]
