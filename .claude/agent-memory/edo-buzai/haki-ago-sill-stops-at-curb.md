---
name: haki-ago-sill-stops-at-curb
description: 張り出し付きの吐き口 AH_Ago は敷き石を縁石の外の面(0.27)で止め、口の先は土の床で塞ぐ。石を板の帯へ延ばすと区画の線の外へ出る(2026-10-13 岡部 EDO-0502 第129巡の差し戻し)
metadata:
  type: project
---
- 硬い区域は「石」で数える(EdoBuild.MizoStoneXMax = 材 rocks・Gravel の局所 +X の最大 ≤ 型 A の石の外の面)。土の板は柔らかい張り出しで線を越えてよいが、石を板の帯へ延ばすと ⛔。
- 口の先(xc〜xc+0.40)を空けると板の小口の間から地形の下の空が抜ける ⇒ 板と同じ材の土の床(天端 = 敷き石 −0.002 → 外の縁 −0.03)で塞ぐ。ago_side(prof=) で断面を渡す。
**How to apply:** 区画の線へ口を向ける駒は、石の外形を線の内に閉じ、外へ出す物は土の材だけにする。検算は FBX を読み (−x, z, −y) で材ごとの +X 最大を測る。関連 [[mizo-ago-terrain-sawtooth]] [[haisui-modules-holes-and-soil-scale]]
