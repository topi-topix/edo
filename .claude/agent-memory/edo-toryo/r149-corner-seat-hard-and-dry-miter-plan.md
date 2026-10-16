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

**第149巡の続き(S1→S2 だけ流した)の罠**
- 指図のコミット(bc0fa15d)の後は算出物の指紋で S1 が止まる+ graded.bin も古い ⇒ `bake_impl.py okabe --write` → `impl_okabe.py --graded-bin`(80 秒)→ 静的な _graded を reflection で null → S1(3 行目が 0.25m の bin か見る)。S1→S2 は 79 秒で MCP は時間切れ(印のファイルで待つ)。
- `MiterBaseWait` の倍率は**次の辺の側だけ**。前の辺の端の駒は倍率(P14 1/0.5・P19 0.25/0.75・P41 0.25/0.5)も種類(坂なりの GU/GD 駒・短く切った _L 駒)も違う ⇒ 部材方へは据わった両脇の端の駒を測って渡す(scratchpad r149/base_ends.txt の型)。
- 素の版(Nagaya_Omote_<run>_2f)が無い棟は建たず、その頂点の留めは**測られない**(N16_k/N16_0/N17_0 の頂点16・17)⇒ 隣の棟の θ が 0 に化ける(N15_0 が mc-89x0 を要ると出た)。留めの版の前に素の版の待ちを見る。
