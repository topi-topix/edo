---
name: toe-bench-cut-and-joint-cover
description: 法尻の野面石の背の小段(toeBench)は「切る」BackBench の裏返し ── 群の外接で守ると全部守る・天端の最大で小段を引くと継ぎ目の低い石の天端に被りが残る
metadata:
  type: project
---
2026-10-06 EDO-0502 第33巡。`EdoBuild.ToeBenchOf/ToeBenchAt/ToeBenchWrite`(EdoBuildSaka.cs)を入れ、岡部 Stage2b が地形を切り Stage3b/GradeQA が同じ式を読む。被り 15→6。

1. 建物・塀を守る keep を「群の子の外接(RB)」で取ると、Buildings の子は棟の組で外接が広く、切る節点 1203 のうち 1182 を守って何も切れなかった。
   **MeshRenderer ごとの bounds** にしたら守ったのは 6。keep は「切る所だけ問う」順にしないと数が嘘になる。
2. 小段の高さを 0.25m の帯ごとの**駒の最上点 − 0.05** で引くと、run の継ぎ目(辺24 の 098f/099f・天端 11.78/11.76)で石の上面が帯の最大より
   0.14 低く、皮が 0.09〜0.2 被る(皮は設計 11.73 よりさらに 11.84 へ上がっていた ── CutEdgeSkin の縁の閉じのどれか・未特定)。
3. 差し込んだ端(nozuraEndRule ④)は「端の先 0.3m・奥行の中ほどの設計の地盤 > 天端 + 0.1」で見分け、小段を半駒手前で止め、先は 1:1.5 の円錐で切る(最大 1.27m)。

**How to apply:** 継ぎ目の被りを詰めるなら、小段の高さを帯の最大でなく背の縁の石の上面(局所の Top)で引く型を足す。守りは部材ごとの外接で。
関連: [[nozura-end-rule-blocked-by-back-soil]] [[koshi-end-cut-exceeds-on-1to1-slope]] [[fumiishi-chamfer-and-floor-cover]]
