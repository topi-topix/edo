---
name: mizo-piece-depth-includes-rim-and-skin-covers
description: DoiMizo の駒は名の深さ+縁0.02で、名で選ぶと5駒ごとに浮いて落ちる。皮の後に置いた溝は皮と地形に覆われる
metadata:
  type: project
---

症状: 岡部 N39_0 の背の雨落ち(DoiMizo 型A)が 18 駒中 4〜5 駒「浮く駒」で据わらず途切れた(2026-10-10 第80巡)。
原因: Doi_Mizo_A_D0.10 の実測の深さは 0.120(D0.15=0.169・D0.20=0.218)。名の深さで選ぶと縁の分だけ天端が地面+topAbove を越え LayMizo の硬い検めで消える。頭の底も名の 0.10 で解くと頭の駒が浮く。
対処: 駒は MizoPieceOf(path).Depth ≤ need+topAbove で最も深い物・depthMin は最も浅い駒の実測の深さ(PlaceBackGutters)。

もう一つ: 皮(Stage3b)の後に置いた溝は、皮(16.50 の面)と穴でない升の地形が溝の中を覆う(18 駒中 13)。溝は皮の部材の一覧に入れて皮より先に置かないと見えない。

**Why:** 溝の駒は縁を持つので名と実寸が違う。皮は渡された部材しか避けない。
**How to apply:** 溝を据える型を書くときは実測の深さで選び、皮のある邸では Stage3b の皮の前に置いて parts へ渡す。
関連: Stage3b が 68 分かかった回はスワップ 8.7/9.2GB(RSS 0.8GB)── 止まっていない。sample で JIT の番地が進むかで見分ける。
