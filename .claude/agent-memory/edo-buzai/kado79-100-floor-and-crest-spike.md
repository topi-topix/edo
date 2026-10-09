---
name: kado79-100-floor-and-crest-spike
description: 折れ 79° の隅は腕2 の先の裏石が腕1 の奥を囲み目地が穴になる・100° の a は天端の列の石の 1 点が +0.18 出る ── make_kado_deg に底の板の延長と天端への下ろしを足した(2026-10-09 EDO-0502)
metadata:
  type: project
---
第66巡で Kado100/Kado79 × H4800 と G−495/−660 × H3000〜4800 を staging/buzai_kado66 に焼いた。
- φ<90 では腕2 の先の裏石(U1B+)が腕1 の先の奥(面から 0.76〜1.0)の背に回り、直線の駒では背へ抜けていた目地が holes の「囲まれた穴」になる。margin を 1.0 にしても消えない ⇒ kado_deg_ura に底の板 ura_floor_kd(奥 0.98)を足した。
- φ=100.2 の a は st_Ka52I の背の 1 点が天端 +0.18 ⇒ 凸包で尖り。make_kado_deg で天端より上の点を h へ下ろす(上に出ていない駒は不変)。
**Why:** 新しい角は既存の角で通った検算が通る保証が無い。
**How to apply:** 隅の駒を焼いたら必ず holes と crest を staging で回す。[[kado103-and-grade-per-meter]] [[nozura-kado-deg-per-stone-and-crest-slabs]]
