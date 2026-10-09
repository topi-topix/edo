---
name: kado103-and-grade-per-meter
description: 野面の勾配の駒の G は m あたりの勾配(1 駒の落差ではない)・指図の「G−1200 で 1.2 下ろす」は G−660 で焼いた・鈍い折れ 103° の隅の駒の継ぎ目の差は裏石の帯の食い込み(2026-10-09 EDO-0502)
metadata:
  type: project
---
第65巡で Kado103_H4800_a/b と H1800〜2400 × G−495/−660 × a〜d を staging/buzai_kado65 に焼いた。
- **G は m あたり**(wall_P: 天端 = h + g·s・C# も maxGrade/m・sinkGrade·W)。普請方の指図と依頼は「G−900/G−1200 = 1 駒で 0.9/1.2 下がる」と読んでいた ⇒ 字面どおり焼くと 1 駒で 1.64/2.18 下がり 1:0.8 になる。意図(1.818 で 0.9/1.2・≈1:1.5)の −0.495/−0.660 で焼き、名もその値。
- 103.4° の b は腕2 の先に「隅の駒だけ」の点 4(面から 0.57〜0.59・天端)── 裏石が隣の裏石へ食い込むだけ。check_kado_deg は口(直線だけの点)と面の列(FACE_ROW 内)の余りだけ落とすようにした。
- render_grade は急な勾配だと 3 駒で床の下へ沈み seam 図が空になる ⇒ 平・勾配・平の 1 駒で撮る(scratchpad の render_steep.py の型)。

**Why:** 指図の数値が駒の名の単位と食い違っても、誰も気づかずに字面で焼く。
**How to apply:** 勾配の駒の依頼は「1 駒の落差か m あたりか」を名の式で確かめてから焼く。[[nozura-end-caps-per-stone]] [[nozura-kado-oblique-fold]]
