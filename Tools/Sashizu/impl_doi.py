"""土井の算出物の器(EDO-0533)。`bake_impl.py doi --write` が呼ぶ。

⭕ `graded` はいまの生成器(`build_sashizu.Model.graded_y` → `sashizu_lib.graded_y`)で世界の 1m 格子を焼く
  (岡部 `impl_okabe.bake_graded` と同じ手)。図で検めた地盤と建てる地盤が同じ物になる ──
  ⛔ 旧 `EdoDoiBuilder.DesignY/GradedY`(矩形の段・C# への写し)は案A の多角形の段と折れ線の坂を読めない。
⛔ `corners` は焼かない ── 土井の runs は seat が null の地形なりの区間を持ち、共通の焼き手(rseat)が読めない(外周の Stage で決める)。
⛔ planting / gardens / base はまだ器に入れていない — 返さない(bake_impl が据え置きとして名指しで刷る)。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_sashizu as B  # noqa: E402
import bake_impl as BI     # noqa: E402
import impl_okabe as IO    # noqa: E402

EST = "doi"


def bake():
    M = B.Model(EST)
    poly = BI.parcel_poly(EST)
    d = json.load(open(os.path.join(B.DOC, EST + "_sashizu.json"), encoding="utf-8"))
    p = os.path.join(B.DOC, EST + "_impl.json")
    im = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return {"graded": IO.bake_graded(M, poly)}
