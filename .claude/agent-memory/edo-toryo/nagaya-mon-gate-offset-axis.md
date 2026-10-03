---
name: nagaya-mon-gate-offset-axis
description: 門長屋の FBX(Nagaya_Omote_<len>_mon<gc>)の口の芯はローカル +X で len/2 − gc。指図の口の s から gc を出すには据えた駒の +X の向きが要る
metadata:
  type: project
---

門長屋の FBX `Nagaya_Omote_<len>_mon<gc>_2f` の口の芯は**ローカル +X = len/2 − gc**(生成器の `--gate` は「左端から」だが Unity では +X 端から測った値になる)。2026-10-03 に 17.68_mon5.5 / 20.07_mon16 の奥の壁(z≈−4.35)の抜けを測って確かめた(芯 +3.34 / −5.96)。表の壁の側は扉で埋まっているので、抜けは奥の壁で測る。

**Why:** 岡部 案1 の指図は門長屋の口を `komon[].s` / `gate.s`(辺の走り)で持つ。辺の向きと駒の +X が逆になる(sSign −1)と、口は s0 + gc に来る。向きを式で決めると口が反対の端に出る。

**How to apply:** 口の s から gc を出すのは据えた後の実ベクトル(sSign)で: gc = len/2 − sSign·(s − sMid)。岡部の N39_0・N18_0 は sSign **+1** で gc = s1 − s(17.68_mon12.18・20.07_mon4.07)。指図が書いた mon5.5 / mon16(gc = s − s0)は口が反対の端に出た(s=12.2・4.0)── `EdoOkabeYashikiBuilder.GateInNagaya` が測って版を引き直す。
