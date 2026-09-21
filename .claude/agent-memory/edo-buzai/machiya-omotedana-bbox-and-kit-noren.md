---
name: machiya-omotedana-bbox-and-kit-noren
description: 表店の駒が食う幅は軒込みの bbox(MachiyaRun)・瓦の唇と袖瓦が名目の足形より外へ出る・キットに本物の暖簾と犬矢来がある(2026-09-21 EDO-0348)
metadata:
  type: project
---

5間の表店 `Typ_Omotedana_5ken` を起こしたときに押さえたもの。町屋の駒はすべてこの系。

**Why:** 「桁行5間」を柱通りで取ると、`MachiyaRun` が食う幅は 9.45 になり表の 9.09 と 0.36m ずれる。

**How to apply:**
- ⭐ **`EdoBuild.ShopModule.W` は `FaceSpan(…, MinValue, MaxValue)`= 軒込みの端**で、run は
  その幅をカーソルに積む。⇒ **表の間口 = bbox の X** にすること。柱通りはそこから内へ引く
  (5間なら柱間 1.750m = 0.96間)。⛔ 柱間を 1.818 固定にしない。
- **名目の軒先線より外へ出る量は瓦モジュール由来の定数**(実測・動かせない):
  流れ方向 **+0.0805**(軒瓦の唇)/ けらば方向 **END + 袖瓦幅/2 − 袖瓦の寄せ**。
  ⇒ `hw = W/2 − OVER_X`, `hd = D/2 − OVER_Z` で逆算し、**焼いた直後に bbox を注文と突き合わせる**。
- ⭐⭐ **キットに本物の暖簾がある** — `Props/Noren A(2.72×2.17)/ B(1.82×0.44)/ C(1.78×0.43)`、
  材 `Noren` / `Noren 1` / **`Noren 2`(_ColorB 0.30/0.36/0.61 = 藍)**。アルベドは無地の布で、
  **色は Unity の .mat が `Noren Color Mask` で乗せる** ⇒ Blender のレンダでは白いまま。
  ⛔ 箱に `wall A` を貼って暖簾にしない(障子と同じ白板になって立面から消える)。
  同じ棚に **犬矢来 `Props/Inuyarai_A_01_x1/2/4/8`(材 `Inuyarai_A`・2間で 3.64×1.36)** もある。
- ⛔ **`Eg.Shop01/02` の材 `shop01map`/`shop02map` は借りられない** — obj 埋め込みで `.mat` 資産が
  無く remap の借り先に出ない。⇒ 並べ比べでは **`es_shop01/shop01.jpg` を手で結線する**。
  結ばないと在庫が**真っ白の箱**で並び、軒高が合っているかを読めない。
- 4間より深い町屋を**1枚の切妻**で架けると棟が 5.4m まで上がる(勾配 0.5456 は動かせない)。
  ⇒ **表屋(厨子二階)+ 奥(平屋)の段違い**。奥棟の前流れは表屋の裏壁へ**谷**で当たるので
  雨押えで塞ぐ。関連 [[dan-chigai-roof-kuchi-is-a-duct]] [[small-roof-tile-scale-and-panel-gaps]]
