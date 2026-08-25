# -*- coding: utf-8 -*-
"""指図生成器(build_*_sashizu.py)の共通ライブラリ。

**バイト同一のものだけを置く。** 4本の生成器から、空白正規化なしの完全一致で
同一と実証できた関数・クラスのみをここへ移す(本体は一切変更しない)。
邸ごとに分岐した検査関数(overlap_check / kenpei / graded_y / md2html /
section_svg / main 等)は各生成器に残してある — 統一は別途裁定の上で行う。

- `_SVN` は SVG 図版番号のカウンタ。各生成器の `_sv()`(図版を開く関数、生成器ごとに
  defs が異なるため各自が持つ)が `from sashizu_lib import _SVN` で同じ list を
  参照して増やし、ここの `_pat()` がそれを読む。
"""

_SVN = [0]


def _pat(): return "url(#pi%d)" % _SVN[0]


def R(x, y, w, h, fill="none", stroke="none", sw=1.0, dash=None, op=None):
    a = '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"' % (x, y, w, h, fill)
    if stroke != "none":
        a += ' stroke="%s" stroke-width="%.2f"' % (stroke, sw)
    if dash:
        a += ' stroke-dasharray="%s"' % dash
    if op is not None:
        a += ' opacity="%.2f"' % op
    return a + "/>"
