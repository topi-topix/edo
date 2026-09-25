---
name: fill-only-floor-and-base-facing
description: 山王 v16(2026-09-25)で踏んだ三つ ── 盛土の床を皮の面にすると垂直の土が立つ・基壇の向きを同族の重心で決めると門で割れた塊で裏返る・設計面の縁の値を外へ平らに延ばすと溝
metadata:
  type: project
---

EDO-0430 回廊の基壇を一段にして流し直したとき。

1. **盛土の床(terraces[].fillOnly)は皮の面(SkinFace)にしない。** 床の高さは下限で graded は max(床, 地山)。面にすると皮が多角形の中を床の高さへ平らに削り、東の見え面の前に高さ 1.2m の垂直な土が立った。→ SkinFaces で除外。
2. **基壇(受け高が全て負)の見え面の向きは、端で継ぐ基壇の壁の走りの逆**(EdoBuild.BlockOutward)。同族の重心から外へ、では楼門で南北に割れた回廊で妻の石垣が塊の内へ向き、地表の LowSide は隣の見え面の前の低い地盤が 2m 格子で滲んで裏返った。
3. **皮の DesignOut は設計面の外の節点を地形で埋める。** 無い節点を落として残りで割ると縁の値が 1m 外まで平らに延び、登る地形との間に幅 1m・深さ 0.2〜0.35m の溝。
4. sealFace は面の外(設計の地盤)にも同じ許容で効かせ、底は半格子で・鉛直な面の下の縁は 0.2m 以内で取る(0.6m だと段ごとに底が上がる袖で下の段の縁を拾い 0.08 足りない)。

**How to apply:** 整地を流したら数値の前に見え面の前を斜めから一枚撮る。溝は窪みの走査(0.75m 両側より 0.12m 低い点)で拾える。
関連: [[run-corners-seams-and-tiers]] [[grade-transfer-cliff-and-dropped-cells]] [[backfill-skin-needs-three-limits]]
