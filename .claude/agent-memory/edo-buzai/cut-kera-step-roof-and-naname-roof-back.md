---
name: cut-kera-step-roof-and-naname-roof-back
description: 座の違う留めの屋根は高い方=袖瓦+鬼+白い妻・低い方=袖瓦(--cut-kera)。斜め端の練塀は長屋の隅の中を通るので屋根は切り口より内へ引く。写真の塊・割れ目は隣の駒のことが多い(2026-10-16 岡部 第146巡)
metadata:
  type: project
---
- 座の違う二棟を二等分の面で切ると、切りっぱなしの瓦の列が相手の屋根へ段違いに乗り上げて見える ⇒ `build_nagaya_omote --cut-kera <−X> <+X>`(hi/lo/0)。延ばした妻の在庫の袖瓦・鬼に面属性 "kera" を打ち(join・積み・bisect を経ても残る)、写して剪断で切り口へ沿わせる。hi の断面の板は全部白壁(破風の木にすると妻に黒い三角)。名・札の長さ・GUID は不変、札は source と height(鬼 +0.065)・eave.z0(袖瓦 −0.03)だけ変わる。
- `Neribei_Naname_*` は相手の長屋の隅の中を斜めに通り、切り口だけが正面(浮き彫りの出 +0.03)に出る ⇒ 屋根は切り口より駒の内へ 0.06 引く(外へ差し込む向きに足すと破片が増えた)。向きは「切り口の板=留めの柱が見えている側が外」で読む。
- 写真の「塊」「割れ目」はまず prefab の TRS で組んで色分けして持ち主を確かめる: P40 の塊 = 溝の隅の桝 D_Corner_Masu、P12 左下の冠瓦 = 隣の類型邸 sannobuke_juge の土塀、冠瓦の割れ目 = Saka_T11|Kado_18M の継ぎ目(隙 0)と隅駒の留め線。光線は面の上ちょうどを避けて半刻みずらす。

**How to apply:** 座の違う留めの版を焼くときは prefab の座で hi/lo を決めて --cut-kera を付ける(float の双子名も同じ引数で)。関連 [[nagaya-miter-cut-signed-anchor-seal]] [[miter-both-ends-length-overshoot]] [[dobei-kiri-hand-and-gable-cut]] [[kado-seam-inward-and-prefab-rays]]
