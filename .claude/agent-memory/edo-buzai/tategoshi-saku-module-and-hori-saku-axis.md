---
name: tategoshi-saku-module-and-hori-saku-axis
description: 竪格子の柵 1間(2026-10-02)— 袖の意匠は build_machikido.sode_* を共用・HoriSaku の「杭は −X 端」は VM の走りの反転で実は +X・fence 札の笠木の出は丈の半ばの断面で決まる
metadata:
  type: project
---

2026-10-02 EDO-0503 で `build_tategoshi_saku.py`(`TategoshiSaku_<h>` / `TategoshiSakuPost_<h>`・Models/Hei)を起こした。
- 町木戸の袖を `sode_uvs/sode_post/sode_kasagi/sode_jifuku/sode_koshi` に切り出して共用。切り出しの前後で町木戸の面の集合(頂点+UV)の sha1 が一致することを確かめた。
- ⚠ `build_hori_saku.py` は杭を走り x = −0.909 に置き「−X 端」と書くが、VM.Mesh は Unity X = −x なので Unity では **+X 端**(FBX を読み直すと Blender x 0..0.15 = Unity −0.15..0)。新しい駒は Unity の値で考え `U(a,b)=(−b,−a)` で写す。
- fence 札の `copingOverhang` は `EdoPartSpec.Measure` の定義(丈の半ばの断面の端から外形の端まで)に揃えないと Verify が落ちる。格子の駒なら最後の竪子から端までの 0.056 になる(笠木が出ているのではない)。
**How to apply:** 検め画像の run は元の駒を原点に残したまま写しを並べるので、元の物は `hide_render` で隠す(写しは継ぐので戻す)。関連 [[logical-axis-and-mirror-checks]]
