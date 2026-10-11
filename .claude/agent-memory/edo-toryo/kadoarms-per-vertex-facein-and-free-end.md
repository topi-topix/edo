---
name: kadoarms-per-vertex-facein-and-free-end
description: KadoArms は頂点ごとに faceIn(両辺の外面の深い方)を取るので同じ辺の両端の腕が食い違う(辺2 で 0.23 重なり・辺3 で 0.31 の口)・隅でない端(留め柱・長屋の妻)は腕に上限が掛からず P1 を 0.75 越えた
metadata:
  type: project
---

2026-10-12 EDO-0502 第115巡(岡部 角 P0 の南 P2〜P4・部材方が焼いた A226x60 / A50x70 を据えた)。

1. **症状**: 辺3 の P3 の出の腕の先 s2.22・P4 の入りの腕の先 s2.53 ⇒ 0.31m の口(S_Hei_01c は「0.31 据えない」)。辺2 は P2/P3 の腕が 0.23 重なる。
   **原因**: PlaceKado は頂点ごとに `fiK = max(FaceIn(入りの辺の終わり), FaceIn(出の辺の始め))` を KadoArms へ渡す ⇒ 同じ辺 e を両端の頂点が別の pivotIn で割り、share が揃わない。
   **対処(この巡)**: Stage2 の run の据えで、両端が隅の腕の 0.01〜0.5 の口は中ほどに 0.5 の駒を据えて腕へ重ねて埋める。根は KadoArms(辺ごとに一つの faceIn で割る)── 直すと部材の名が変わる(部材方へ)。
2. **症状**: P2 の入りの腕 2.26 間(4.11m)が辺1(3.31m)を越え、P1 の先 0.75 まで(N41_5 の妻の中・留め柱を貫く)。S_Hei_01 は「−0.83 据えない」。
   **原因**: 辺の相手の端が隅でなければ maxJ = L − bodyIn·tanH(入隅 −1)で、入隅の先へ腕が伸びてよい扱い(相手の辺に練塀が続く前提)。留め柱・長屋の妻で止まる端を知らない。
3. Stage1 の 1 行目が「0.25m の造成の面が古い指図から焼かれている」なら `impl_okabe.py --graded-bin`(79 秒)→ `Reload()` → Stage1。指図の上書きの後は毎回。

4. 練塀の内の足元の帯(EdoBuild.WriteFootBand): 内面を辺ごとの最大で取ると隅の駒 Dobei_Kado_00 の内(直線の駒より +0.55)を拾い帯が 0.55 奥へずれた ⇒ 駒ごとの 95% 点(FootLine.DInAt)。
   摺り付け(1/3)を溝の床の辺(野面石との間)にも掛けると野面石の背の小段を 1.55 削った ⇒ 摺り付けは欄の feather.side(路地の側)の辺だけ。2b は 15 分 ── 試すなら帯の関数だけ reflection で dry-run(SeRojiHeiFoot(false))。
5. LayDanOchi の段数を ceil(落差/0.45) にすると R0.45 の駒の実の 1段 0.461 が上限 0.45 を越え ⛔ ⇒ 段数は ceil(落差/(上限−0.05))。

**How to apply:** 名指しの腕の版を据えたら、Stage2 の「隅の腕(壁体・実測)」の行で同じ辺の両端の s を突き合わせる(口・重なり・辺の外)。
関連: [[scaled-kado-height-and-named-arm-parts]] [[kado-arm-overruns-short-edge]]
