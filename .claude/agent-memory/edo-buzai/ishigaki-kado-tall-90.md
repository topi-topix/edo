---
name: ishigaki-kado-tall-90
description: 石垣の隅を 4m より高く・90° で焼くとき — 丈は勾配の段を下へ継ぎ足す・出隅の張り出しが 1 モジュールを越える
metadata:
  type: project
---

2026-09-25・山王 回廊の基壇 NE 隅(`Ishigaki_Kado_90_H0500`)で踏んだ。

- Castle Wall の面は一枚の平面 x + 0.25·z = 2.4。丈は最下段(1m)を複製し面の頂点だけ段ごとに +0.25 出して継ぐ(`build_kado.py --h`)。⛔ z の引き伸ばしは石が縦に伸びる。
- Δ=90° だと張り出し 2.4〜2.65 m が −Y 側 1 枚(2.0)を越え、隅の足に穴が開く ⇒ n_neg を厚み·tan(Δ/2) から決めるよう直した。
- +deg が出隅(面が凸)、M が入隅。90° の出隅は対称なので + だけで両回りに足りる(yaw で腕を選ぶ)。

**Why:** 山王の基壇は天端 29.00 で足元が 4m より下がる所があり、素の Corner(4m・1.1m の大面取り)では足りない。
**How to apply:** 別の丈・角度は `--h <m> --deg <角>` で焼き `Own.IshigakiKado(deg,h)` で引く。関連 [[kado-mitre-parts]]
