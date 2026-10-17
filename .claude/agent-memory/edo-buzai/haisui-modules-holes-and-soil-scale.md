---
name: haisui-modules-holes-and-soil-scale
description: 地盤の下へ潜る排水の駒は「口・切り欠き・隙」から地形の下の空が抜ける。FJG Soil は 8m 周期・実岩は fill 1.25(2026-10-04 土井 S9 排水 build_doi_haisui.py)
metadata:
  type: project
---
- 天端を地盤に据えて潜る部材(溝・桝・段落ち)は、桝の入口の切り欠き・吐き口の奥・蹴込みの足元の 4cm の隙から**地形の下の空**が見える(マゼンタで出た)。⭕ 切り欠きは溝が必ず付く所だけ・口の奥は石樋の筒+塞ぎ石・水叩きは蹴込みの下へ潜らせる。実岩を立てた側壁は岩の間が抜ける ⇒ 面を揺らした切石を2段に積む。
- FJG Soil の茶の矩形を 16m 周期で貼ると松葉が拡大されて橙の筋になる ⇒ 地形の L_dirt と同じ 8m。実岩を bbox の長径で寸法合わせすると見えの径は 0.8 倍 ⇒ 玉石は fill 1.25 で詰める。
- 検めの空のマゼンタは Light Path の Is Camera Ray で混ぜる(背景色を直に替えると照明ごと桃色に染まる)。
**How to apply:** 地中へ潜る部材すべて。関連 [[magenta-background-finds-holes]] [[join-uv-layer-names-and-rock-color-match]]
