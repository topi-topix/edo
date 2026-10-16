---
name: r149-corner-seat-hard-and-dry-miter-plan
description: 第149巡 岡部 — 角の座の違いは MiterPerimeterCorners が硬く退ける・流さず要る留めの版を出すのは PlanCornerMiters(Group を呼ばない)
metadata:
  type: project
---

- 角で座が違う二棟は `EdoBuild.CornerSeatMismatch` で【硬】二棟とも建てない(直角の角も検める・座は欄の両端 seatLo/seatHi)。旧い seatNote(注記だけ)は退役。
- 流さない一覧は `EdoOkabeYashikiBuilder.PlanCornerMiters(path)` → `EdoBuild.MiterNeedPlan`。**Group() を呼ぶと解いて書き戻しの台帳に載る**ので GameObject.Find で読むだけにした。
  外面の控えは今据わっている同じ辺の長屋の札で測る ⇒ 台の控えが変わる辺(岡部 辺12〜15)は要る長さが c·tan(θ/2) 動く(θ11.5° で c+0.25 → +0.025)。正は流しの S2 の待ち。
- 台の Castle Wall の留めの版(MiterBaseWait)は倍率と天端が S2 の据えから出るので、流さずに出せるのは区画の折れだけ。

**Why:** 施主裁定 案A 2026-10-16(角で一棟に見えること・oki-kata §2a)。
**How to apply:** 流す前に部材方へ版を頼むときは PlanCornerMiters を打つ。流した後は S2 の待ちの行と突き合わせる。
