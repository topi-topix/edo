---
name: machikido-keisha-warp
description: 町木戸の横断勾配の版(2026-10-02)— 平らに組んでから m.v を y の一次で縦剪断する warp・札の勾配の欄・Verify は斜めの足元を測れない
metadata:
  type: project
---

2026-10-02 EDO-0503 で `build_machikido.py --keisha <m>` を足した(`MachiKido_<haba>_k<k>`・負は `km`)。
- 組み方: 平らに組み、部品ごとに `warp(m, i0, ya, fa, yb, fb)` で高さだけ一次で動かす(袖=全剪断・親柱=頭固定で足だけ・沓石=芯の地面へ平行移動・開いた扉=吊り元の地面)。竪は鉛直のまま。⚠ VM.Mesh の走りは Unity X の逆なので地面は `ground_u(-x)`。
- 検算は FBX を (−x, z, −y) で読み、z=0 の線を 1cm 刻みで下から光線 → 地面より上で当たる所 0。⛔ 頂点を 0.1m の筋で数えると長い箱の中ほどが「浮き」に見える(偽陽性)。
**How to apply:** 札は yBottom=下手の根・jamb の帯はその端の地面から。追加欄 `keisha/ground/contactPts` は C# の Spec に無く JsonUtility が捨てる ── `EdoPartSpec.Measure/Verify` は最下点+0.05 で足元を切るので斜めの部材では足元が下手の端柱だけになる。呼び出し元へ必ず添える。
