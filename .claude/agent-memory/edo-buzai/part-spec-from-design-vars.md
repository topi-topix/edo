---
name: part-spec-from-design-vars
description: 部材の札(PartSpecs json)は作図の変数から書き、出荷済み FBX は焼き直さず --spec-only で札だけ書く。検算は FBX を (-x, z, -y) で Unity 局所へ写して Measure を再現する
metadata:
  type: project
---

2026-09-29 EDO-0491 で門 3 型(+Munamon の 2.7/Open)の札を書いた。出荷済み FBX は 09-04 の Blender 製なので焼き直さず `--spec-only` で札だけ書いた。
**Why:** 札の帯(底+0.30)は沓石の天端(敷居+0.05)の 1cm 下を切るので、front/back と脇の z には沓石の寸法が入る。開いた版の扉は軒の外(−Z)へ振れ出るので、外接箱も扉まで広げないと嘘になる。
**How to apply:** 検算は `UserData/EDO0491/specs/{dump.py,check.py}`。Blender で FBX を読み、(−x, z, −y) で Unity 局所へ写して `EdoPartSpec.Measure` と同じ手続きを回す。6 本とも差 0.000 だった。⚠ Measure の通り口の読み方は、閉じた版で本柱の内の面より 0.014 内側、開いた版では振れた扉を拾って 0.23〜0.27 内側になる。札は本柱の内の面(±hx)。Verify は通り口の値を比べないので今は落ちない。
