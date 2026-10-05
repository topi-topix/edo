---
name: overlap-run-abuts-to-zero
description: 上手の run の裏へ重ねて埋める短い run を PlaceNozuraNet に渡すと、端を近くの駒へ突き付けて縮み駒が 0 になる ── NozuraSeg.noAbut で打ち切りにする
metadata:
  type: project
---

2026-10-05 EDO-0502 第24巡(岡部 腰石垣の返し・指図「1 駒より短い run は余りを上手へ重ねて埋める」)。

症状: RunsByCrestGap で 1.82m に延ばした run(始まりが前の run の終わりより手前)が「始まり 相手の面へ s=1.02 / 終わり s=0.49」で駒 0。返しの先 0.7m が抜けた。
原因: PlaceNozuraNet の端の決め ③(端から 1.5m 内の据わった駒の実面へ突き付け)が、重ねた先の上手の駒を相手に取る。
対処: NozuraSeg.noAbut[端] = true で打ち切り(ビルダーは前の run の b より a が手前なら両端に立てる)。

**How to apply:** 区間を重ねて渡すときは、2b のログの「⇒ 駒 0」を先に grep する。岡部 2b は 11 秒・3b は 6.5〜8 分。
⚠ 残り: 西の返しの末端の背の角(-529.2, 948.0)で駒の底 20.20 > 描かれた地表 19.93(小段の式は 20.32 なのに描かれていない)・溝の中に土の尾根(表 1m で 19.8〜19.9)。
関連: [[short-return-tie-and-sode-extent]] [[nozura-dan-piece-fixed-height]]
