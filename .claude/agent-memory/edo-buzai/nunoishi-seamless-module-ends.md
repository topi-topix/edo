---
name: nunoishi-seamless-module-ends
description: 並べて継ぐ石積みの駒は端の平面の稜を面取りしない・写しは元の hide_render を継ぐ(2026-09-29 練塀の布石 Dobei2m_Nunoishi)
metadata:
  type: project
---

練塀の布石(`build_dobei_nunoishi.py`・EDO-0477)で決めた・踏んだこと。

- ⭕ 走りに並べる石積みの駒は、縦目地を駒の中だけに置き、**端の平面 x=0 / x=L に乗る稜は面取りしない**。
  目地の集合を [0,L) で決めれば並べて自動で周期になり、端の石が継ぎ目を跨いで1枚に見える。
  ⛔ 端まで面取りすると継ぎ目ごとに縦の溝が立つ。目地は端から 0.14 以上離す。
- ⚠ 面取り 2 セグメントで 1472 三角形(Dobei2m 404 の 3.6 倍)。1 セグメント + 常に埋まる下端の稜を除いて 608。
- ⚠ レンダで元を `hide_render=True` にしてから `copy()` すると**写しも隠れる**(地面しか写らない画を刷った)。写しで False に戻す。

**How to apply:** 塀・石垣の駒を新造するときは端の稜の扱いを先に決める。関連 [[magenta-background-finds-holes]]
