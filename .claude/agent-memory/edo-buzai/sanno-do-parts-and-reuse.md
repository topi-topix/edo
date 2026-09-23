---
name: sanno-do-parts-and-reuse
description: 山王の未実装10棟は6型で足りる。厩・蔵は既存の附属屋の生成器に引数を足して呼ぶだけ・鼓楼は鐘楼に太鼓を吊るだけ。斜材を箱で段に積まない
metadata:
  type: project
---

2026-09-22(EDO-0261)。指図 `sanno_sashizu.json` の `munes[]` 10 棟は **丈と柱割が無い**
(`hFrom`/`bays`/`partFrom` の 3 欄が欠ける)。部材方が【U】で起こした値は
`Tools/Blender/build_sanno_do.py` の docstring と `EdoAssets.Own.SannoDo/SannoInari/
SannoUmaya/SannoKura` の XML に置いた。⛔ ここに数を写さない(二重になる)。

**⭕ 新しく躯体を書き起こしたのは堂宇と稲荷社だけ。**残りは既存の生成器に引数を足した:
- **御厩** = `build_okabe_fuzokuya.umaya(uKen=3, vKen=4, eaveH=2.55, frontH=1.15, noki=0.70)`
  ── 類型の `Typ_Umaya` と**同じ呼び出し**。⚠ ローカル **+X = 桁行(vKen)**。
- **御蔵** = `build_matsudaira_dewa_fuzokuya.dozo(..., okiyane=0.42)`。**`okiyane` は 2026-09-22 に足した**
  (既定 0.0 で従来と寸分同じ)。置屋根 = **漆喰の塗屋根 + 小屋束 + 桁**を入れて瓦を持ち上げる作り。
  ⛔ 空く帯を塞がない(通気がこの作りの目的)。⛔ 塗屋根を省かない(省くと帯から本当に空が抜ける)。
  ⚠ `dozo` は長手を +X に焼くので、山王の約束(ローカル X = 東 = u)へ **90° 振ってから**書き出す。
- **鼓楼** = `build_typ_jisha.shoro(taiko=True)`。**`taiko` は 2026-09-22 に足した** — 躯体は鐘楼と
  寸分同じで、吊る物を梵鐘 → 太鼓に替えるだけ。鼓面は ±Z。
- **鐘楼** = 在庫の `Typ_Shoro_3ken`(基壇 3 間角が指図の 3×3 間にそのまま合う)。焼き直さない。

⛔ **軸平行の箱を段に積んで斜材を作らない。** 稲荷社の千木と破風でやったら**階段状の輪郭**に
なって木の板に見えなかった。⭕ `SH.stick`(2点を結ぶ角材)で継ぐ。同じ理由で木階の側桁も
床まで落とした板にしない(木箱に見える)。

⚠ **一間社は指図の矩形より小さい。** 稲荷社の `du`/`dv` は 3×3 間(5.454角)だが、一間社春日造は
身舎が 1 間角と決まった形式なので実寸 3.03 × 4.48。⛔ 引き伸ばさない — 指図の矩形は
「据え場所の取り」と読む(普請奉行へ申し送り済み)。

⚠ **御蔵の漆喰 `Wall Exterior Defence` は Japanese Castle の材**(土蔵の生成器を借りた帰結)。
山王の remap の `donorDirs` に `Japanese Castle/Meshes/Exterior/Materials` を足した。
⇒ **生成器を他邸から借りたら、その材の .mat が remap の借り先に在るか必ず確かめる。**

関連 [[hip-roof-noji-and-ridge-axis]] [[kirishi-tile-and-shu-material]]
[[narabe-check-and-fbx-byte-noise]]
