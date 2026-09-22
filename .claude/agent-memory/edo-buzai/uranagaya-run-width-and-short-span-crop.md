---
name: uranagaya-run-width-and-short-span-crop
description: 裏長屋が列で食う走りは ken×1.818 + 0.540 で一定(けらば+袖瓦)・短い桁行では立面レンダが縦に切れる(2026-09-22)
metadata:
  type: project
---

**裏長屋 `Typ_UraNagaya_<ken>ken[_munewari]` が列で食う走りは `ken × 1.818 + 0.540` で、
全寸法(3 / 4.5 / 6 / 9 / 12間)で一定。** 内訳はけらば 0.20×2 + 袖瓦の見付 0.07×2。
高さ・奥行は桁行に依らず **割長屋 H 3.592 / D 4.928・棟割 H 4.584 / D 8.564**(底 0.000)。

**Why:** 2026-09-22 に EDO-0362 で 4.5間・3間を足したとき、5寸法を同じ物差しで測り直して確かめた
(6/9/12 は 11.448 / 16.902 / 22.356 で既存の XML コメントと 1mm も違わなかった)。
呼び寸法 `ken×1.818` で詰めると 1棟ごとに 0.54m ずつ食い違う。表店で同じ罠を踏んでいる
→ [[machiya-omotedana-bbox-and-kit-noren]]。

**How to apply:** 列へ詰める側(`EdoBuildMachiya.UraNagayaRun`)は既に `OwnMeasure(path).W` で
実寸を引いているので、**寸法を足すときは FBX を焼くだけでよく C# は触らない**
(`EdoAssets.Own.UraNagaya(float)` は `Len2()` で任意の ken を解く。`fmt()` と同じ丸め)。
⚠ ただし `OwnMeasure` は Unity に取り込まれていない FBX では値が出ない — 焼いた後の import は必須。

---

⛔ **`build_typ_nagaya.shots()` の立面は短い桁行で縦に切れる。**
`ortho_scale = max(W,H)*1.15` を res 2000×900(縦横比 2.22)へ渡すので、
**W が H の 2.2 倍より短い棟**(3間: W 5.99 / H 3.59)では大棟と鬼が画面の外へ出る。
⇒ 3間・4.5間の可否は `*_elev.png` でなく **`*_gable.png`(res 1200×1100)と `*_3d.png`** で読む。
⚠ 「屋根が写っていない = 欠陥」と誤診しかけた。カメラは bbox から引いていても**縦横比を掛け忘れる**。
→ 同種の話 [[narabe-check-and-fbx-byte-noise]]
