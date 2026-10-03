---
name: kabukimon-nosode-and-leaf-meet-gap
description: 袖なし冠木門を起こしたとき — edogoyomi の obj は頂点が g 行の前に来るので群の実測は面から取る・棟門の leaf(meet=) の定規縁は召し合わせの隙を塞がない・全幅2間の縛りは冠木の鼻で吸う
metadata:
  type: project
---

2026-09-30 EDO-0491 で `build_kabukimon.py`(袖なし冠木門 `Kabukimon_NoSode_2.73`)を起こした。
- edogoyomi の obj(Yet Another OBJ Exporter)は**頂点が `g` 行の前**に並ぶ。頂点で群を切ると名前が1つずれる → 群の寸法は `f` が引く頂点から取る(`scratchpad objcomp.py` の手)。
- `build_munamon.leaf(meet=)` の定規縁は隙の**脇**(0.012〜0.067)に付き、召し合わせの 24mm の隙が正面立面で空の筋になる。棟門・薬医門・山門にも同じ筋があるはず(未直し)。新しい門では隙の真後ろに縁を打つ。
**How to apply:** 門を起こしたら正面の ortho で扉の芯に筋が無いか見る。全幅の上限が硬いときは本柱を細め、冠木の鼻で吸う(在庫の鼻 0.466 は 2間に入らない)。
