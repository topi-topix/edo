---
name: roof-atlas-rect-and-soban-ray
description: 瓦の役物(袖瓦)に roof アトラスの sample_uv_bright ±0.04 の矩形を貼ると野地の木の帯に掛かって茶色の板になる。塀と門の当たりを真上の光線で測ると足元の頂点が礎盤に当たって軒の値が隠れる
metadata:
  type: project
---

2026-09-14 山王の袖塀(`build_sanno_sodebei.py`)で踏んだ二つ。
・袖瓦の UV を `V.sample_uv_bright(roof 2x2, "roof")` の ±0.04 矩形にしたら、袖垂れが**茶色の木目の板**になった。`Dobei2m_End` と同じ `V.sample_uv(pick_high=True)` の ±0.01 に戻して灰色に直った。
・塀の頂点から楼門 FBX へ真上に光線を当てると、足元の頂点が**礎盤(丈 0.15)**に当たり「最小の離れ 0.150」と出て、軒との離れ(1.395)が見えなかった。

**Why:** roof アトラスは瓦と木部が同居していて、明るさで選んだ点の周りでも木の帯に掛かる。光線の最小値は一番下の材で決まる。
**How to apply:** 瓦の役物は既存部材の取り方に揃え、端のレンダで色を見る。当たりは「足元の食い込み」と「軒との離れ」を別々に刷る(軒は 1.0 m より上の材だけ)。関連 [[noji-under-tile-valley]]
