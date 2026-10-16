---
name: r150-kidan-tome-placement
description: 第150巡 岡部 — 台の石垣の浅い出隅の留めの版は札の Q へ寄せるだけでは据わらない(控え c と倍率の違い・一つずつ引いた端の駒)・S2 は FillConvexCornerSlits を二度呼ぶ・長屋の留めの版は乾いた見込みでなく S2 の待ちの長さで焼く
metadata:
  type: project
---
2026-10-16 EDO-0502 第150巡(EdoBuild.SwapEndsToTome・FillConvexCornerSlits の pieces 引数)。

1. **札の据え(tomeCrestFrontCorner を両脇の天端の前の縁の線の交点 Q へ)が効くのは、端の駒が Q で終わる角だけ**(P8/P9/P13/P39 は寄せ 0.001)。
   控え c が違う浅い角(P14 1.0/0.5・3.4°)は Q が 8.4m 先、一つずつ内へ引いた端の駒(P19)は 2.2m 先、短い _L 駒(P35)は隣と 0.27 の口、P41 は隣の駒が版の先を 0.15 越えた。
   **対処**: 札の Q → 片側だけ寄せ → 半分ずつ、を据えて【硬】区域・隣の駒が版の奥の端を跨ぐ・版の先を越えない、で選ぶ。版の奥の端より角の側に丸ごと在る駒は版に替わられた残りとして退ける(P19 で 3 駒)。9/10 で継ぎ目 0。
2. **S2 のログに出る FillConvexCornerSlits の行は一度目の呼び**。S2 は台を二度据え(天端の線の座から据え直す)、二度目の行はログに出ない ⇒ 結果は `EdoBuild.TomeBaseLog` / `MiterBaseWait`(静的)を S2 の直後に刷る。⭕だけの行はログから落ちる。
3. 長屋の留めの版を PlanCornerMiters(乾いた見込み)の長さで焼くと、台の控えが変わる辺で 0.005〜0.03 外れて建たない(N15_0・N16_0・N17_0・N17_k)。⇒ 部材方へは **S2 の「要る版 … 長さ Q〜反対の端」**の行を渡す。
4. S1+S2 は 0.3 分(2 回目以降)。2b は長いので、S2 の待ちが 0 になってから 2b へ進む(待ちがあるまま 2b を流すと全部やり直し)。

**How to apply:** 台の留めの待ちは S2 の後に TomeBaseLog を読む。長屋の版の注文は S2 の待ちの行から。関連 [[r149-corner-seat-hard-and-dry-miter-plan]] [[okabe-perimeter-rerun-order-and-neribei-measure]]
